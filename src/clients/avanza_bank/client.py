import json
import time
from datetime import date
from functools import cache
from typing import List, Optional, Union

import keyring
from avanza import Avanza as AvanzaBase
from avanza import InstrumentType, OrderType, Resolution, TimePeriod, constants
from avanza.models import WatchList
from requests.exceptions import HTTPError

from src.clients.avanza_bank.models import (
    AccountOverview,
    AccountsPositions,
    CallRequest,
    DeleteOrderResponse,
    EditOrderResponse,
    InstrumentCertificate,
    InstrumentIndex,
    InstrumentStock,
    InstrumentWarrant,
    OrderException,
    Orders,
    PlaceOrderResponse,
    SearchResult,
)
from src.clients.avanza_bank.models.chart_data import ChartData
from src.data.settings import USERNAME
from src.utils.logger import get_logger

log = get_logger("clients.avanza_bank.client")


class Avanza(AvanzaBase):
    def _retry_call(
        self,
        path: str,
        http_method: str = "GET",
        options: Optional[dict] = None,
    ) -> dict:
        request = CallRequest(
            path=path,
            method=http_method,
            options=options,
        ).model_dump()

        response = {}
        for _ in range(10):
            try:
                response = self.__call(**request, return_content=True)

            except HTTPError:
                time.sleep(5)

            if response:
                return response if isinstance(response, dict) else json.loads(response, parse_float=float)

        log.error(f"Failed to get {path}")
        return {}

    def get_chart_data(
        self,
        order_book_id: str,
        period: TimePeriod,
        resolution: Optional[Resolution] = None,
    ) -> Optional[ChartData]:
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

    def get_accounts_overview(self) -> AccountOverview:
        data = self._retry_call("/_api/account-performance/overview/total-values")

        return AccountOverview(**data)

    def get_watchlists(self) -> List[WatchList]:
        data = super().get_watchlists()

        return [WatchList(**i) for i in data]  # type: ignore

    def search_instrument(
        self,
        search_string: str,
        types: List[Union[InstrumentType, str]],
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
        data = super().get_accounts_positions()

        return AccountsPositions(**data)  # type: ignore

    def list_orders(self) -> Orders:
        data = self._retry_call("/_api/trading/rest/orders")

        return Orders(**data)

    def place_order(
        self,
        account_id: str,
        order_book_id: str,
        order_type: OrderType,
        price: float,
        valid_until: date,
        volume: int,
    ) -> Optional[str]:
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

    def delete_order(self, account_id, order_id: str) -> Optional[str]:
        response = super().delete_order(account_id, order_id)

        if not response:
            raise OrderException("Failed to delete order (Unknown reason)")

        parsed_response = DeleteOrderResponse(**response)
        if parsed_response.order_request_status != "SUCCESS":
            raise OrderException(
                f"Failed to delete order ({parsed_response.message_code})",
            )

        return parsed_response.order_id


@cache
def get_client(user: str = USERNAME) -> Avanza:
    """time is a dummy argument to make the function bypass the cache once every hour"""

    log.debug("Connecting to Avanza")

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
