from unittest import TestCase

import numpy as np
import pandas as pd

from services.ta.indicators.trend import Trend


def _bars(bars: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(5)
    close = 400 * np.exp(np.cumsum(rng.normal(0, 0.004, bars)))
    index = pd.date_range("2026-01-05 15:30", periods=bars, freq="30min")
    return pd.DataFrame(
        {"Open": close, "High": close * 1.002, "Low": close * 0.998, "Close": close, "Volume": 1000},
        index=index,
    )


class Test_AverageDirectionalMovement(TestCase):
    def test_lensig_smooths_the_adx_line_and_the_indicator_is_added(self):
        short_smoothing, long_smoothing = _bars(), _bars()
        short_trend, long_trend = Trend(short_smoothing), Trend(long_smoothing)
        short_trend.add_average_directional_movement(length=11, lensig=5, mamode="rma")
        long_trend.add_average_directional_movement(length=11, lensig=30, mamode="rma")

        # The library used to drop `lensig` silently; the ADX column is named after it
        assert "ADX" in short_trend.indicators and "ADX" in long_trend.indicators
        common = short_smoothing["ADX_5"].dropna().index.intersection(long_smoothing["ADX_30"].dropna().index)
        assert not np.allclose(short_smoothing.loc[common, "ADX_5"], long_smoothing.loc[common, "ADX_30"])
        assert short_smoothing["DMP_11"].equals(long_smoothing["DMP_11"])
