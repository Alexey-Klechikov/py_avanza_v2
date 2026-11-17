from datetime import date
from unittest import TestCase

import numpy as np
import pandas as pd

from services.storage.candle_quality import CandleQuality, DataQualityError, require_clean_bars

COMPLETE_DAY = date(2026, 8, 3)
PARTIAL_DAY = date(2026, 8, 4)


def _day_of_candles(day: date, complete: bool, bars: int = 60) -> pd.DataFrame:
    """A random walk sampled into 2-minute candles; partial candles only see their first seconds."""
    rng = np.random.default_rng(day.toordinal())
    prices = 3000 + np.cumsum(rng.normal(0, 0.15, size=bars * 20))
    rows = []
    for number in range(bars):
        ticks = prices[number * 20 : (number + 1) * 20] if complete else prices[number * 20 : number * 20 + 1]
        rows.append((ticks[0], ticks.max(), ticks.min(), ticks[-1], 0))

    index = pd.date_range(f"{day} 10:00", periods=bars, freq="2min")
    return pd.DataFrame(rows, index=index, columns=["Open", "High", "Low", "Close", "Volume"])


class Test_CandleQuality(TestCase):
    bars = pd.concat([_day_of_candles(COMPLETE_DAY, complete=True), _day_of_candles(PARTIAL_DAY, complete=False)])

    def test_detects_partial_candle_days(self):
        quality = CandleQuality.of(self.bars)

        assert quality.clean_days == [COMPLETE_DAY]
        assert quality.partial_days == [PARTIAL_DAY]
        assert quality.clean_share == 0.5

    def test_require_clean_bars_drops_partial_days(self):
        clean_bars = require_clean_bars(self.bars, min_clean_share=0.5)

        assert set(clean_bars.index.date) == {COMPLETE_DAY}

    def test_require_clean_bars_stops_on_too_little_clean_data(self):
        with self.assertRaises(DataQualityError):
            require_clean_bars(self.bars, min_clean_share=0.8)
