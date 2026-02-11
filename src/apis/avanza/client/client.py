import json
import os
import time
from collections.abc import Sequence
from dataclasses import dataclass
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
from apis.avanza.client.models.instrument.etf import InstrumentETF
from apis.avanza.client.models.instrument.fund import InstrumentFund
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

log = get_logger()


RETRY_ATTEMPTS = int(os.getenv("AVANZA_RETRY_ATTEMPTS", "10"))
RETRY_BACKOFF_SECONDS = int(os.getenv("AVANZA_RETRY_BACKOFF_SECONDS", "3"))
CHART_DATA_RETRY_ATTEMPTS = int(os.getenv("AVANZA_CHART_DATA_RETRY_ATTEMPTS", "120"))
CHART_DATA_RETRY_SLEEP_SECONDS = int(os.getenv("AVANZA_CHART_DATA_RETRY_SLEEP_SECONDS", "30"))
CONNECT_RETRY_ATTEMPTS: int | None = None
CONNECT_RETRY_BACKOFF_SECONDS = int(os.getenv("AVANZA_CONNECT_RETRY_BACKOFF_SECONDS", "2"))


@dataclass
class Endpoints:
    chart_data = "/_api/price-chart/stock/{order_book_id}"
    instrument = "/_api/market-guide/{type}/{id}"
    instrument_details = "/_api/market-guide/{type}/{id}/details"
    index = "/_api/market-index/{id}"
    index_details = "/_api/market-index/{id}/details"
    etf = "/_api/market-etf/{id}"
    etf_details = "/_api/market-etf/{id}/details"
    fund_references = "/_api/fund-reference/reference/{id}"
    fund_sustainability = "/_api/fund-reference/sustainability/{id}"
    fund_portfolio = "/_api/fund-reference/portfolio-data/{id}"
    fund_trading_terms = "/_api/fund-guide/fund-trading-terms/{id}"
    accounts_overview = "/_api/account-performance/overview/total-values"
    watchlists = "/_api/watchlist/watchlist"
    filtered_search = "/_api/search/filtered-search"
    accounts_positions = "/_api/position-data/positions"
    list_orders = "/_api/trading/rest/orders"
    transactions_list = "/_api/transactions/list"
    watchlist_remove = "/_api/watchlist/watchlist/remove/{watchlist_id}/{instrument_id}"
    watchlist_add = "/_api/watchlist/watchlist/add/{watchlist_id}/{instrument_id}"
    place_order = "/_api/trading-critical/rest/order/place"
    edit_order = "/_api/trading-critical/rest/order/modify"
    delete_order = "/_api/trading-critical/rest/order/delete"
    market_stocks_filter = "/_api/market-stock-filter/stocks"


class Avanza(AvanzaBase):
    def __init__(self, credentials: dict[str, str]):
        super().__init__(credentials)
        self._authentication_session = None

    def _retry_call(self, method: HttpMethod, path: str, options: dict | list | None = None) -> dict:
        response: dict | str | None = None
        for i in range(RETRY_ATTEMPTS):
            try:
                response = self.__call(method=method, path=path, options=options, return_content=True)

            except HTTPError as e:
                log.debug(e)
                time.sleep((i + 1) * RETRY_BACKOFF_SECONDS)

            if response:
                if isinstance(response, dict):
                    return response

                try:
                    return json.loads(response, parse_float=float)
                except JSONDecodeError as exc:
                    log.error(f"Failed to decode JSON response for {method} {path}: {exc}")
                    return {}

        log.error(f"Failed request after retries: {method} {path} (attempts={RETRY_ATTEMPTS})")
        return {}

    def get_chart_data(
        self,
        order_book_id: str,
        period: TimePeriod,
        resolution: Resolution | None = None,
    ) -> ChartData | None:
        options = {"timePeriod": period.value.lower()}
        if resolution is not None:
            options["resolution"] = resolution.value.lower()

        response: dict | None = None
        for _ in range(CHART_DATA_RETRY_ATTEMPTS):
            try:
                response = self.__call(
                    method=HttpMethod.GET,
                    path=Endpoints.chart_data.format(order_book_id=order_book_id),
                    options=options,
                )

                if response:
                    return ChartData(**response)

            except HTTPError:
                time.sleep(CHART_DATA_RETRY_SLEEP_SECONDS)

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

        combined_response = {}
        for path in endpoints:
            response = self._retry_call(
                method=HttpMethod.GET,
                path=path.format(type=instrument_type.value, id=instrument_id),
            )

            if response:
                combined_response.update(response)

        return combined_response

    def get_instrument_certificate(self, instrument_id: str) -> InstrumentCertificate:
        data = self._get_instrument(instrument_type=InstrumentType.CERTIFICATE, instrument_id=instrument_id)

        return InstrumentCertificate(**data)

    def get_instrument_warrant(self, instrument_id: str) -> InstrumentWarrant:
        data = self._get_instrument(instrument_type=InstrumentType.WARRANT, instrument_id=instrument_id)

        return InstrumentWarrant(**data)

    def get_instrument_stock(self, instrument_id: str) -> InstrumentStock:
        data = self._get_instrument(instrument_type=InstrumentType.STOCK, instrument_id=instrument_id)

        return InstrumentStock(**data)

    def get_instrument_index(self, instrument_id: str) -> InstrumentIndex:
        data = self._get_instrument(
            instrument_type=InstrumentType.INDEX,
            instrument_id=instrument_id,
            endpoints=[Endpoints.index],
        )

        return InstrumentIndex(**data)

    def get_instrument_etf(self, instrument_id: str) -> InstrumentETF:
        data = self._get_instrument(
            instrument_type=InstrumentType.EXCHANGE_TRADED_FUND,
            instrument_id=instrument_id,
            endpoints=[Endpoints.etf, Endpoints.etf_details],
        )

        return InstrumentETF(**data)

    def get_instrument_fund(self, instrument_id: str) -> InstrumentFund:
        data = self._get_instrument(
            instrument_type=InstrumentType.FUND,
            instrument_id=instrument_id,
            endpoints=[
                Endpoints.fund_references,
                Endpoints.fund_sustainability,
                Endpoints.fund_portfolio,
                Endpoints.fund_trading_terms,
            ],
        )

        return InstrumentFund(**data)

    def get_accounts_overview(self, account_url_parameter: str) -> AccountOverview:
        data = self._retry_call(
            method=HttpMethod.POST,
            path=Endpoints.accounts_overview,
            options=[account_url_parameter],
        )

        return AccountOverview(**data)

    def get_watchlists(self) -> list[Watchlist]:
        data = self._retry_call(method=HttpMethod.GET, path=Endpoints.watchlists)
        if not isinstance(data, list):
            log.error("Unexpected watchlists response type")
            return []

        return [Watchlist(**i) for i in data]  # type: ignore

    def filtered_search(self, search_string: str, types: list[InstrumentType | str]) -> SearchResult:
        data = self._retry_call(
            method=HttpMethod.POST,
            path=Endpoints.filtered_search,
            options={
                "query": search_string,
                "searchFilter": {"types": [i.name if isinstance(i, InstrumentType) else i for i in types]},
                "pagination": {"from": 0, "size": 200},
            },
        )

        return SearchResult(**data)

    def get_accounts_positions(self) -> AccountsPositions:
        data = self._retry_call(method=HttpMethod.GET, path=Endpoints.accounts_positions)

        return AccountsPositions(**data)

    def list_orders(self) -> Orders:
        data = self._retry_call(method=HttpMethod.GET, path=Endpoints.list_orders)

        return Orders(**data)

    def get_transactions(
        self,
        transaction_details_types: Sequence[TransactionsDetailsType],
        transactions_from: date,
        transactions_to: date | None = None,
        max_elements: int | None = 1000,
        account_id: str | None = None,
    ) -> TransactionsDetails:
        data = self._retry_call(
            method=HttpMethod.GET,
            path=Endpoints.transactions_list,
            options={
                "transactionTypes": ",".join([type.value for type in transaction_details_types]),
                "from": transactions_from.isoformat(),
                "to": transactions_to.isoformat() if transactions_to else None,
                "maxElements": max_elements,
                "accountIds": account_id,
            },
        )

        return TransactionsDetails(**data)

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
        response = super().place_order(
            account_id=account_id,
            order_book_id=order_book_id,
            order_type=order_type,
            price=price,
            valid_until=valid_until,
            volume=volume,
        )

        if not response:
            raise OrderException("Failed to place order (Unknown reason)")

        parsed_response = PlaceOrderResponse(**response)
        if parsed_response.order_request_status != "SUCCESS":
            raise OrderException(f"Failed to place order ({parsed_response.message_code})")

        return parsed_response.order_id

    def edit_order(self, order_id: str, account_id: str, price: float, valid_until: date, volume: int, *_):
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
        response = super().delete_order(account_id, order_id)

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

    i = 0
    while True:
        try:
            client = Avanza(credentials)  # type: ignore
            return client

        except HTTPError as e:
            log.error(e)
            i += 1

            if CONNECT_RETRY_ATTEMPTS is not None and i >= CONNECT_RETRY_ATTEMPTS:
                raise

            time.sleep(i * CONNECT_RETRY_BACKOFF_SECONDS)
