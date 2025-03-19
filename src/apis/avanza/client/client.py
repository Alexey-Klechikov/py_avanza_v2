import json
import time
from collections.abc import Sequence
from copy import copy
from datetime import date
from functools import lru_cache

import keyring
from avanza import Avanza as AvanzaBase
from avanza import InstrumentType, OrderType, Resolution, TimePeriod, constants
from avanza.constants import TransactionsDetailsType
from requests.exceptions import HTTPError

from apis.avanza.client.models.account.overview import AccountOverview
from apis.avanza.client.models.account.positions import AccountsPositions
from apis.avanza.client.models.account.watchlists import Watchlist
from apis.avanza.client.models.call_request import CallRequest
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
from apis.avanza.client.models.search.market_stocks_result import MarketStocksFilterResult
from config import ACCOUNT_USERNAME
from utils.logger import get_logger

log = get_logger()


class Avanza(AvanzaBase):
    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self._authentication_session = None

    def _retry_call(
        self,
        path: str,
        http_method: str = "GET",
        options: dict | list | None = None,
    ) -> dict:
        request = CallRequest(
            path=path,
            method=http_method,
            options=options,
        ).model_dump()

        response = {}
        for i in range(10):
            try:
                response = self.__call(**request, return_content=True)

            except HTTPError as e:
                log.debug(e)
                time.sleep((i + 1) * 3)

            if response:
                return response if isinstance(response, dict) else json.loads(response, parse_float=float)

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

        for _ in range(2 * 60):
            try:
                response = self.__call(
                    constants.HttpMethod.GET,
                    f"/_api/price-chart/stock/{order_book_id}",
                    options,
                )

            except HTTPError:
                time.sleep(30)

        if response:
            return ChartData(**response)

        log.error(f"Failed to get chart data for {order_book_id}")

    def _get_instrument(
        self,
        instrument_type: InstrumentType,
        instrument_id: str,
    ) -> dict:
        result = {}

        for path in [
            "/_api/market-guide/{}/{}",
            "/_api/market-guide/{}/{}/details",
        ]:
            response = self._retry_call(
                path.format(instrument_type.value, instrument_id),
            )

            if response:
                result.update(response)

        return result

    def get_instrument_certificate(self, instrument_id: str) -> InstrumentCertificate:
        data = self._get_instrument(InstrumentType.CERTIFICATE, instrument_id)

        return InstrumentCertificate(**data)

    def get_instrument_warrant(self, instrument_id: str) -> InstrumentWarrant:
        data = self._get_instrument(InstrumentType.WARRANT, instrument_id)

        return InstrumentWarrant(**data)

    def get_instrument_stock(self, instrument_id: str) -> InstrumentStock:
        data = self._get_instrument(InstrumentType.STOCK, instrument_id)

        return InstrumentStock(**data)

    def get_instrument_index(self, instrument_id: str) -> InstrumentIndex:
        data = self._get_instrument(InstrumentType.STOCK, instrument_id)

        return InstrumentIndex(**data)

    def get_accounts_overview(self, account_url_parameter: str) -> AccountOverview:
        data = self._retry_call(
            "/_api/account-performance/overview/total-values",
            http_method="POST",
            options=[account_url_parameter],
        )

        return AccountOverview(**data)

    def get_watchlists(self) -> list[Watchlist]:
        data = self._retry_call(
            "/_api/watchlist/watchlist",
            http_method="GET",
        )

        return [Watchlist(**i) for i in data]  # type: ignore

    def filtered_search(
        self,
        search_string: str,
        types: list[InstrumentType | str],
    ) -> SearchResult:
        data = self._retry_call(
            path="/_api/search/filtered-search",
            http_method="POST",
            options={
                "query": search_string,
                "searchFilter": {
                    "types": [i.name if isinstance(i, InstrumentType) else i for i in types],
                },
                "pagination": {"from": 0, "size": 200},
            },
        )

        return SearchResult(**data)

    def get_accounts_positions(self) -> AccountsPositions:
        data = self._retry_call("/_api/position-data/positions")

        return AccountsPositions(**data)  # type: ignore

    def list_orders(self) -> Orders:
        data = self._retry_call("/_api/trading/rest/orders")

        return Orders(**data)

    def get_transactions(
        self,
        transaction_details_types: Sequence[TransactionsDetailsType],
        transactions_from: date,
        transactions_to: date | None = None,
        isin: str | None = None,
        max_elements: int | None = 1000,
    ) -> TransactionsDetails:
        data = super().get_transactions_details(
            transaction_details_types,
            transactions_from,
            transactions_to,
            isin,
            max_elements,
        )

        return TransactionsDetails(**data)  # type: ignore

    def remove_from_watchlist(self, instrument_id: str, watchlist_id: str):
        self._retry_call(
            path=f"/_api/watchlist/watchlist/remove/{watchlist_id}/{instrument_id}",
            http_method="POST",
        )

    def add_to_watchlist(self, instrument_id: str, watchlist_id: str) -> None:
        self._retry_call(
            path=f"/_api/watchlist/watchlist/add/{watchlist_id}/{instrument_id}",
            http_method="POST",
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
            raise OrderException(
                f"Failed to place order ({parsed_response.message_code})",
            )

        return parsed_response.order_id

    def edit_order(
        self,
        order_id: str,
        account_id: str,
        price: float,
        valid_until: date,
        volume: int,
        **_,
    ):
        response = self._retry_call(
            path="/_api/trading-critical/rest/order/modify",
            http_method="POST",
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
            raise OrderException(
                f"Failed to edit order ({parsed_response.message_code})",
            )

        return parsed_response.order_id

    def delete_order(self, account_id, order_id: str) -> str | None:
        response = super().delete_order(account_id, order_id)

        if not response:
            raise OrderException("Failed to delete order (Unknown reason)")

        parsed_response = DeleteOrderResponse(**response)
        if parsed_response.order_request_status != "SUCCESS":
            raise OrderException(
                f"Failed to delete order ({parsed_response.message_code})",
            )

        return parsed_response.order_id

    def get_market_stocks(
        self,
        market_places: list[str] = copy(["se"]),
        offset: int = 0,
        limit: int = 100,
    ) -> MarketStocksFilterResult:
        response = self._retry_call(
            path="/_api/market-stock-filter/stocks",
            http_method="POST",
            options={
                "filter": {"marketPlaces": market_places},
                "offset": offset,
                "limit": limit,
                "sortBy": {"order": "desc", "field": "numberOfOwners"},
            },
        )

        return MarketStocksFilterResult(**response)  # type: ignore


@lru_cache
def get_client(user: str = ACCOUNT_USERNAME) -> Avanza:
    log.debug("Connect to Avanza")

    credentials = {
        "username": keyring.get_password(user, "un"),
        "password": keyring.get_password(user, "pass"),
        "totpSecret": keyring.get_password(user, "totp"),
    }

    if [i for i in credentials.values() if i is None]:
        log.error("Missing credentials")
        raise ValueError

    i = 1
    while True:
        try:
            client = Avanza(credentials)  # type: ignore
            return client

        except HTTPError as e:
            log.error(e)
            i += 1

            time.sleep(i * 2)
