from unittest import TestCase
from unittest.mock import patch

import pandas as pd

from apis.yahoo.client.models.history_request import Interval, Period
from apis.yahoo.operators.ticker import Ticker


def _chunk(start: str) -> pd.DataFrame:
    index = pd.date_range(start=start, periods=2, freq="2min", tz="America/New_York")
    return pd.DataFrame(
        {"Open": [1.0, 1.1], "High": [2.0, 2.1], "Low": [0.5, 0.6], "Close": [1.5, 1.6], "Volume": [10, 11]},
        index=index,
    )


class TestTicker(TestCase):
    def test_short_period_uses_single_request_in_stockholm_time(self):
        with patch("apis.yahoo.operators.ticker.Yahoo.get_history", return_value=_chunk("2026-11-18 09:30")) as fetch:
            history = Ticker().get_history(period=Period.ONE_DAY, interval=Interval.TWO_MINUTES)

        fetch.assert_called_once_with(period=Period.ONE_DAY, interval=Interval.TWO_MINUTES)
        self.assertEqual(history.index.name, "Datetime")
        self.assertIsNone(history.index.tz)
        self.assertEqual(history.index[0], pd.Timestamp("2026-11-18 15:30"))

    def test_long_intraday_period_is_fetched_in_capped_five_day_chunks(self):
        with patch(
            "apis.yahoo.operators.ticker.Yahoo.get_history",
            side_effect=lambda **_: _chunk("2026-11-18 09:30"),
        ) as fetch:
            history = Ticker().get_history(period=Period.THREE_MONTHS, interval=Interval.TWO_MINUTES)

        # 42 available days plus tomorrow -> 44 dates -> 9 chunks of 5 days
        self.assertEqual(fetch.call_count, 9)
        self.assertEqual(len(history), 2)
