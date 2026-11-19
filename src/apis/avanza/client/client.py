import json
import os
import re
import time
from collections.abc import Sequence
from datetime import date
from functools import lru_cache
from json import JSONDecodeError

from avanza import Avanza as AvanzaBase
from avanza import InstrumentType, OrderType, Resolution, TimePeriod
from avanza.constants import HttpMethod, TransactionsDetailsType
from dotenv import load_dotenv
from requests.exceptions import HTTPError

from apis.avanza.client.models.account.overview import AccountOverview
from apis.avanza.client.models.account.positions import AccountsPositions
from apis.avanza.client.models.account.watchlists import Watchlist
from apis.avanza.client.models.chart_data import ChartData
from apis.avanza.client.models.instrument.certificate import InstrumentCertificate
from apis.avanza.client.models.instrument.index import InstrumentIndex
from apis.avanza.client.models.instrument.stock import InstrumentStock
from apis.avanza.client.models.instrument.warrant import InstrumentWarrant
from apis.avanza.client.models.order.delete import DeleteOrderResponse
from apis.avanza.client.models.order.edit import EditOrderResponse
from apis.avanza.client.models.order.exceptions import OrderException
from apis.avanza.client.models.order.list import Orders
from apis.avanza.client.models.order.place import PlaceOrderResponse
from apis.avanza.client.models.order.transactions import TransactionsDetails
from apis.avanza.client.models.search.filtered_search_result import SearchResult
from utils.logger.operators import get_logger
from utils.retry import backoff_seconds

log = get_logger()


# Every retry loop is bounded and backs off exponentially from its base delay up to its cap (utils.retry)
RETRY_ATTEMPTS = int(os.getenv("AVANZA_RETRY_ATTEMPTS", "10"))
RETRY_BACKOFF_SECONDS = int(os.getenv("AVANZA_RETRY_BACKOFF_SECONDS", "3"))
RETRY_BACKOFF_CAP_SECONDS = int(os.getenv("AVANZA_RETRY_BACKOFF_CAP_SECONDS", "30"))
CHART_DATA_RETRY_ATTEMPTS = int(os.getenv("AVANZA_CHART_DATA_RETRY_ATTEMPTS", "120"))
CHART_DATA_RETRY_BACKOFF_SECONDS = int(os.getenv("AVANZA_CHART_DATA_RETRY_BACKOFF_SECONDS", "2"))
CHART_DATA_RETRY_SLEEP_SECONDS = int(os.getenv("AVANZA_CHART_DATA_RETRY_SLEEP_SECONDS", "30"))  # backoff cap
CONNECT_RETRY_ATTEMPTS = int(os.getenv("AVANZA_CONNECT_RETRY_ATTEMPTS", "10"))
CONNECT_RETRY_BACKOFF_SECONDS = int(os.getenv("AVANZA_CONNECT_RETRY_BACKOFF_SECONDS", "2"))
CONNECT_RETRY_BACKOFF_CAP_SECONDS = int(os.getenv("AVANZA_CONNECT_RETRY_BACKOFF_CAP_SECONDS", "60"))


class Endpoints:
    place_order = "/_api/trading/order-entry/order/new"
    delete_order = "/_api/trading/order-entry/order/delete"
    list_orders = "/_api/trading/trading-orders-and-deals/orders"
    chart_data = "/_api/price-chart/stock/{order_book_id}"
    index = "/_api/market-index/{id}"
    instrument = "/_api/market-guide/{type}/{id}"
    watchlists = "/_api/watchlist/watchlist"
    watchlist_add = "/_api/watchlist/watchlist/add/{watchlist_id}/{instrument_id}"
    watchlist_remove = "/_api/watchlist/watchlist/remove/{watchlist_id}/{instrument_id}"
    filtered_search = "/_api/search/filtered-search"
    accounts_positions = "/_api/position-data/positions"
    accounts_overview = "/_api/account-performance/overview/total-values"
    transactions_list = "/_api/transactions/list"
    edit_order = "/_api/trading/order-entry/order/modify"
    instrument_details = "/_api/market-guide/{type}/{id}/details"


# Avanza returns an empty body on success for watchlist add/remove; only those exact paths skip retrying.
EMPTY_RESPONSE_OK_PATH = re.compile(r"/_api/watchlist/watchlist/(add|remove)/[^/]+/[^/]+")


# Keep the class name `Avanza`: `self.__call` mangles to `_Avanza__call`, the base class's private request method.
# Overrides marked `reportIncompatibleMethodOverride` deliberately return this repo's models and take the arguments
# this repo's orders need, not the library's.
class Avanza(AvanzaBase):
    def __init__(self, credentials: dict[str, str]):
        super().__init__(credentials)
        # Deliberate (2025-03 fix): Avanza rejects requests carrying the X-AuthenticationSession header the library
        # sends. With the token None, requests drops the header and calls authenticate by cookie and security token.
        self._authentication_session = None

    def _retry_call(self, method: HttpMethod, path: str, options: dict | list | None = None) -> dict:
        is_empty_response_ok = EMPTY_RESPONSE_OK_PATH.fullmatch(path) is not None

        for attempt in range(RETRY_ATTEMPTS):
            try:
                response_content = self.__call(method=method, path=path, options=options, return_content=True)

            except HTTPError as exc:
                log.debug(exc)
                time.sleep(backoff_seconds(attempt, RETRY_BACKOFF_SECONDS, RETRY_BACKOFF_CAP_SECONDS))
                continue

            if response_content:
                try:
                    return json.loads(response_content, parse_float=float)
                except JSONDecodeError as exc:
                    log.error(f"Failed to decode JSON response for {method} {path}: {exc}")
                    return {}

            if is_empty_response_ok:
                return {}

            time.sleep(backoff_seconds(attempt, RETRY_BACKOFF_SECONDS, RETRY_BACKOFF_CAP_SECONDS))

        log.error(f"Failed request after retries: {method} {path} (attempts={RETRY_ATTEMPTS})")
        return {}

    def get_chart_data(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        order_book_id: str,
        period: TimePeriod,
        resolution: Resolution | None = None,
    ) -> ChartData | None:
        options = {"timePeriod": period.value.lower()}
        if resolution is not None:
            options["resolution"] = resolution.value.lower()

        for attempt in range(CHART_DATA_RETRY_ATTEMPTS):
            try:
                chart_payload = self.__call(
                    method=HttpMethod.GET,
                    path=Endpoints.chart_data.format(order_book_id=order_book_id),
                    options=options,
                )

                if chart_payload:
                    return ChartData(**chart_payload)

            except HTTPError as exc:
                log.debug(exc)

            time.sleep(backoff_seconds(attempt, CHART_DATA_RETRY_BACKOFF_SECONDS, CHART_DATA_RETRY_SLEEP_SECONDS))

        log.error(f"Failed to get chart data for {order_book_id}")
        return None

    def _get_instrument(
        self,
        instrument_type: InstrumentType,
        instrument_id: str,
        endpoints: list[str] | None = None,
    ) -> dict:
        if endpoints is None:
            endpoints = [Endpoints.instrument, Endpoints.instrument_details]

        merged_payload = {}
        for path in endpoints:
            endpoint_payload = self._retry_call(
                method=HttpMethod.GET,
                path=path.format(type=instrument_type.value, id=instrument_id),
            )
            merged_payload.update(endpoint_payload)

        return merged_payload

    def get_instrument_certificate(self, instrument_id: str) -> InstrumentCertificate:
        return InstrumentCertificate(
            **self._get_instrument(instrument_type=InstrumentType.CERTIFICATE, instrument_id=instrument_id),
        )

    def get_instrument_warrant(self, instrument_id: str) -> InstrumentWarrant:
        return InstrumentWarrant(
            **self._get_instrument(instrument_type=InstrumentType.WARRANT, instrument_id=instrument_id),
        )

    def get_instrument_stock(self, instrument_id: str) -> InstrumentStock:
        return InstrumentStock(
            **self._get_instrument(instrument_type=InstrumentType.STOCK, instrument_id=instrument_id),
        )

    def get_instrument_index(self, instrument_id: str) -> InstrumentIndex:
        return InstrumentIndex(
            **self._get_instrument(
                instrument_type=InstrumentType.INDEX,
                instrument_id=instrument_id,
                endpoints=[Endpoints.index],
            ),
        )

    def get_accounts_overview(self, account_url_parameter: str) -> AccountOverview:
        overview_payload = self._retry_call(
            method=HttpMethod.POST,
            path=Endpoints.accounts_overview,
            options=[account_url_parameter],
        )

        return AccountOverview(**overview_payload)

    def get_watchlists(self) -> list[Watchlist]:  # pyright: ignore[reportIncompatibleMethodOverride]
        watchlists_payload = self._retry_call(method=HttpMethod.GET, path=Endpoints.watchlists)
        if not isinstance(watchlists_payload, list):
            log.error("Unexpected watchlists response type")
            return []

        return [Watchlist(**watchlist) for watchlist in watchlists_payload]  # type: ignore

    def filtered_search(self, search_string: str, types: list[InstrumentType | str]) -> SearchResult:
        search_payload = self._retry_call(
            method=HttpMethod.POST,
            path=Endpoints.filtered_search,
            options={
                "query": search_string,
                "searchFilter": {"types": [i.name if isinstance(i, InstrumentType) else i for i in types]},
                "pagination": {"from": 0, "size": 200},
            },
        )

        return SearchResult(**search_payload)

    def get_accounts_positions(self) -> AccountsPositions:  # pyright: ignore[reportIncompatibleMethodOverride]
        return AccountsPositions(**self._retry_call(method=HttpMethod.GET, path=Endpoints.accounts_positions))

    def list_orders(self) -> Orders:
        return Orders(**self._retry_call(method=HttpMethod.GET, path=Endpoints.list_orders))

    def get_transactions(
        self,
        transaction_details_types: Sequence[TransactionsDetailsType],
        transactions_from: date,
        transactions_to: date | None = None,
        max_elements: int | None = 1000,
        account_id: str | None = None,
    ) -> TransactionsDetails:
        transactions_payload = self._retry_call(
            method=HttpMethod.GET,
            path=Endpoints.transactions_list,
            options={
                "transactionTypes": ",".join(details_type.value for details_type in transaction_details_types),
                "from": transactions_from.isoformat(),
                "to": transactions_to.isoformat() if transactions_to else None,
                "maxElements": max_elements,
                "accountIds": account_id,
            },
        )

        return TransactionsDetails(**transactions_payload)

    def remove_from_watchlist(self, instrument_id: str, watchlist_id: str):
        self._retry_call(
            method=HttpMethod.POST,
            path=Endpoints.watchlist_remove.format(watchlist_id=watchlist_id, instrument_id=instrument_id),
        )

    def add_to_watchlist(self, instrument_id: str, watchlist_id: str) -> None:
        self._retry_call(
            method=HttpMethod.POST,
            path=Endpoints.watchlist_add.format(watchlist_id=watchlist_id, instrument_id=instrument_id),
        )

    def place_order(
        self,
        account_id: str,
        order_book_id: str,
        order_type: OrderType,
        price: float,
        valid_until: date,
        volume: int,
    ) -> str | None:

        response = self._retry_call(
            method=HttpMethod.POST,
            path=Endpoints.place_order,
            options={
                "accountId": account_id,
                "orderbookId": order_book_id,
                "side": order_type.value,
                "price": price,
                "validUntil": valid_until.isoformat(),
                "volume": volume,
            },
        )

        if not response:
            raise OrderException("Failed to place order (Unknown reason)")

        parsed_response = PlaceOrderResponse(**response)
        if parsed_response.order_request_status != "SUCCESS":
            raise OrderException(f"Failed to place order ({parsed_response.message_code})")

        return parsed_response.order_id

    def edit_order(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        order_id: str,
        account_id: str,
        price: float,
        valid_until: date,
        volume: int,
    ) -> str | None:
        response = self._retry_call(
            method=HttpMethod.POST,
            path=Endpoints.edit_order,
            options={
                "orderId": order_id,
                "price": price,
                "volume": volume,
                "openVolume": None,
                "accountId": account_id,
                "validUntil": str(valid_until),
                "metadata": {"orderEntryMode": "STANDARD"},
            },
        )

        if not response:
            raise OrderException("Failed to edit order (Unknown reason)")

        parsed_response = EditOrderResponse(**response)
        if parsed_response.order_request_status != "SUCCESS":
            raise OrderException(f"Failed to edit order ({parsed_response.message_code})")

        return parsed_response.order_id

    def delete_order(self, account_id: str, order_id: str) -> str | None:
        response = self._retry_call(
            method=HttpMethod.POST,
            path=Endpoints.delete_order,
            options={"accountId": account_id, "orderId": order_id},
        )

        if not response:
            raise OrderException("Failed to delete order (Unknown reason)")

        parsed_response = DeleteOrderResponse(**response)
        if parsed_response.order_request_status != "SUCCESS":
            raise OrderException(f"Failed to delete order ({parsed_response.message_code})")

        return parsed_response.order_id


@lru_cache
def get_client() -> Avanza:
    log.debug("Connect to Avanza")

    load_dotenv(os.path.join(os.path.dirname(__file__), "../../../config/.env"))

    credentials = {
        "username": os.getenv("AVA_USERNAME"),
        "password": os.getenv("AVA_PASS"),
        "totpSecret": os.getenv("AVA_TOTP"),
    }

    if any(not v for v in credentials.values()):
        log.error("Missing credentials in .env file")
        raise ValueError("Missing Avanza credentials. Check your .env file.")

    for attempt in range(CONNECT_RETRY_ATTEMPTS):
        try:
            return Avanza(credentials)  # type: ignore

        except HTTPError as exc:
            log.error(exc)
            if attempt == CONNECT_RETRY_ATTEMPTS - 1:
                raise

            time.sleep(backoff_seconds(attempt, CONNECT_RETRY_BACKOFF_SECONDS, CONNECT_RETRY_BACKOFF_CAP_SECONDS))

    raise RuntimeError("AVANZA_CONNECT_RETRY_ATTEMPTS must be at least 1")
