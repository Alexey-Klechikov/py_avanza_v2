from unittest import TestCase

import numpy as np
import pandas as pd

from services.ta.indicators.momentum import Momentum


def _bars(bars: int = 400, start_price: float = 400.0) -> pd.DataFrame:
    """A random walk around a stock-like price level: indicator readings must not depend on that level."""
    rng = np.random.default_rng(3)
    close = start_price * np.exp(np.cumsum(rng.normal(0, 0.004, bars)))
    spread = close * 0.002
    index = pd.date_range("2026-01-05 15:30", periods=bars, freq="30min")
    return pd.DataFrame(
        {"Open": close, "High": close + spread, "Low": close - spread, "Close": close, "Volume": 1000},
        index=index,
    )


class Test_CommodityChannelIndex(TestCase):
    def test_matches_the_textbook_formula_on_both_sides_of_zero(self):
        price_bars = _bars()
        Momentum(price_bars).add_commodity_channel_index(length=12, c=0.015)

        typical = (price_bars["High"] + price_bars["Low"] + price_bars["Close"]) / 3
        deviation = typical.rolling(12).apply(lambda window: np.abs(window - window.mean()).mean(), raw=True)
        expected = (typical - typical.rolling(12).mean()) / (0.015 * deviation)
        cci = price_bars["CCI_12_0.015"]

        assert np.allclose(cci.dropna(), expected.dropna())
        assert (cci > 100).mean() > 0.05 and (cci < -100).mean() > 0.05


class Test_SchaffTrendCycle(TestCase):
    def test_stays_in_range_and_follows_both_trends(self):
        price_bars = _bars()
        Momentum(price_bars).add_schaff_trend_cycle(tclength=10, fast=10, slow=20, factor=0.5)
        stc = price_bars["STC_10_10_20_0.5"]

        assert stc.between(0, 100).all()
        assert 0.25 < (stc > 50).mean() < 0.75  # the library version stuck below 50 whenever MACD was negative

    def test_rises_in_an_uptrend_and_falls_in_a_downtrend(self):
        prices = np.r_[np.linspace(100, 150, 60), np.linspace(150, 100, 60)]
        price_bars = pd.DataFrame(
            {"Open": prices, "High": prices + 0.5, "Low": prices - 0.5, "Close": prices, "Volume": 1000},
            index=pd.date_range("2026-01-05", periods=len(prices), freq="30min"),
        )
        Momentum(price_bars).add_schaff_trend_cycle(tclength=10, fast=5, slow=15, factor=0.5)
        stc = price_bars["STC_10_5_15_0.5"]

        assert stc.iloc[40:60].mean() > 50 > stc.iloc[100:120].mean()
