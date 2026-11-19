from datetime import date, datetime
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from avanza.constants import TransactionsDetailsType

from apis.avanza.operators.transactions import Transactions
from config import SETTINGS


def _transaction(kind: TransactionsDetailsType, day: int, volume: float, amount: float, hour: int = 10):
    return SimpleNamespace(
        type=kind,
        date=datetime(2026, 11, day, hour, 0),
        volume=SimpleNamespace(value=volume),
        amount=SimpleNamespace(value=amount),
        account=SimpleNamespace(id=SETTINGS.ACCOUNT_ID),
        instrument_name="BULL TSLA X5 AVA",
    )


SELL = TransactionsDetailsType.SELL
BUY = TransactionsDetailsType.BUY


class TestBuildDeals(TestCase):
    def test_pairs_newest_sell_with_preceding_buy(self):
        newest_first = [
            _transaction(SELL, 18, -10, 1100, hour=15),
            _transaction(BUY, 18, 10, -1000, hour=11),
            _transaction(SELL, 17, -5, 600),
            _transaction(BUY, 17, 5, -500),
        ]

        deals = Transactions()._build_deals({"BULL TSLA X5 AVA": newest_first}, False, date(2026, 11, 18))

        self.assertEqual(
            [(deal.sell.amount.value, deal.buy.amount.value) for deal in deals["BULL TSLA X5 AVA"]],
            [(1100, -1000), (600, -500)],
        )

    def test_only_today_stops_at_first_older_deal(self):
        newest_first = [
            _transaction(SELL, 18, -10, 1100),
            _transaction(BUY, 18, 10, -1000),
            _transaction(SELL, 17, -5, 600),
            _transaction(BUY, 17, 5, -500),
        ]

        deals = Transactions()._build_deals({"BULL TSLA X5 AVA": newest_first}, True, date(2026, 11, 18))

        self.assertEqual(len(deals["BULL TSLA X5 AVA"]), 1)

    def test_drops_instruments_without_closed_deals(self):
        deals = Transactions()._build_deals(
            {"BULL TSLA X5 AVA": [_transaction(BUY, 18, 10, -1000)]},
            False,
            date(2026, 11, 18),
        )

        self.assertEqual(deals, {})


class TestDailyTradingStats(TestCase):
    def test_sums_amount_and_counts_deals_per_day(self):
        transactions = Transactions()
        newest_first = [
            _transaction(SELL, 18, -10, 1100),
            _transaction(BUY, 18, 10, -1000),
            _transaction(SELL, 17, -5, 600),
        ]

        with patch.object(Transactions, "_reload_log", return_value=newest_first):
            stats = transactions.get_daily_trading_stats(date_from=date(2026, 11, 1))

        self.assertEqual(
            stats,
            {"2026-11-18": {"amount": 100, "deals": 1}, "2026-11-17": {"amount": 600, "deals": 0}},
        )
