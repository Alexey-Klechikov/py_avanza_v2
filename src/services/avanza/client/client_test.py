from datetime import date
from unittest import TestCase

from avanza import InstrumentType, OrderType, Resolution, TimePeriod

from data.settings import ACCOUNT_ID
from services.avanza.client.client import get_client
from services.avanza.client.models import (
    AccountOverview,
    AccountsPositions,
    InstrumentCertificate,
    InstrumentIndex,
    InstrumentStock,
    OrderException,
    Orders,
    SearchResult,
)
from services.avanza.client.models.chart_data import ChartData


class Test_AvanzaClient(TestCase):
    def setUp(self) -> None:
        self.client = get_client()

    def test_get_chart_data(self):
        order_book_id = "19002"
        period = TimePeriod.TODAY
        resolution = Resolution.MINUTE

        result = self.client.get_chart_data(order_book_id, period, resolution)

        self.assertIsInstance(result, ChartData)

    def test_get_instrument_certificate(self):
        order_book_id = "1522311"

        result = self.client.get_instrument_certificate(order_book_id)

        self.assertIsInstance(result, InstrumentCertificate)

    def test_get_instrument_stock(self):
        order_book_id = "963856"

        result = self.client.get_instrument_stock(order_book_id)

        self.assertIsInstance(result, InstrumentStock)

    def test_get_instrument_index(self):
        order_book_id = "19002"

        result = self.client.get_instrument_index(order_book_id)

        self.assertIsInstance(result, InstrumentIndex)

    def test_get_accounts_overview(self):
        result = self.client.get_accounts_overview()

        self.assertIsInstance(result, AccountOverview)

    def test_search_instrument(self):
        query = "Tesla"

        result = self.client.search_instrument(query, types=[])

        self.assertIsInstance(result, SearchResult)

        result = self.client.search_instrument(query, types=[InstrumentType.STOCK])

        assert result.total_number_of_hits == 1

    def test_account_positions(self):
        result = self.client.get_accounts_positions()

        self.assertIsInstance(result, AccountsPositions)

    def test_list_orders(self):
        result = self.client.list_orders()

        self.assertIsInstance(result, Orders)

    def test_place_order(self):
        with self.assertRaises(OrderException):
            _ = self.client.place_order(
                account_id=ACCOUNT_ID,
                order_book_id="1757509",
                order_type=OrderType.BUY,
                price=1,
                valid_until=date.today(),
                volume=1000000,
            )

        with self.assertRaises(OrderException):
            _ = self.client.place_order(
                account_id=ACCOUNT_ID,
                order_book_id="1757509",
                order_type=OrderType.SELL,
                price=1000000,
                valid_until=date.today(),
                volume=1,
            )
