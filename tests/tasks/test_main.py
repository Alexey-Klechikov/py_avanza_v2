from datetime import datetime
from unittest import TestCase

import pandas as pd

from src.tasks.main import MarketData


def _market_data(last_bar_start: str, bars: int = 5) -> MarketData:
    market_data = MarketData()
    index = pd.date_range(end=last_bar_start, periods=bars, freq="2min")
    market_data.bars = pd.DataFrame({"Close": [float(number) for number in range(bars)]}, index=index)
    return market_data


class Test_LastCompleteBar(TestCase):
    def test_skips_the_candle_in_progress(self):
        market_data = _market_data(last_bar_start="2026-11-17 10:00")  # Avanza returned the 10:00 candle

        position = market_data.last_complete_bar_position(now=datetime(2026, 11, 17, 10, 0, 6))

        assert market_data.bars.index[position] == pd.Timestamp("2026-11-17 09:58")

    def test_uses_the_last_candle_when_no_candle_is_in_progress(self):
        market_data = _market_data(last_bar_start="2026-11-17 09:58")  # Avanza left the 10:00 candle out

        position = market_data.last_complete_bar_position(now=datetime(2026, 11, 17, 10, 0, 6))

        assert market_data.bars.index[position] == pd.Timestamp("2026-11-17 09:58")
