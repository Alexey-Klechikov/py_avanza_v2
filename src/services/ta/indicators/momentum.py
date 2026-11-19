import numpy as np
import pandas as pd
import pandas_ta as ta  # pylint: disable=unused-import # noqa: F401

from services.ta.indicators.models.category_base import IndicatorsCategoryBase
from services.ta.indicators.models.indicator import Indicator, IndicatorSignal
from utils.logger.operators import get_logger

log = get_logger()


class Momentum(IndicatorsCategoryBase):
    def add_schaff_trend_cycle(self, tclength: int, fast: int, slow: int, factor: float) -> None:
        """
        STC (Schaff Trend Cycle)
        https://www.prorealcode.com/prorealtime-indicators/schaff-trend-cycle2/
        https://www.investopedia.com/articles/forex/10/schaff-trend-cycle-indicator.asp

        default: tclength=10, fast=12, slow=26, factor=0.5

        The STC is designed to identify trends and trend reversals by measuring the strength of the trend and
        the speed of price changes. The STC is an oscillator, which means that it measures the velocity of price
        movements.

        One version of the STC calculation is the subtraction of the 23-period exponential moving average (EMA)
        from a 50-period EMA. The resulting value is then smoothed using a 10-period moving average (MA).
        The STC oscillates between 0 and 100, with values above 50 indicating a bullish trend and values below
        50 indicating a bearish trend.
        """
        column = f"STC_{tclength}_{fast}_{slow}_{factor}"

        # Computed here: pandas_ta 0.4.71b0 only updates its first stochastic while the MACD window's low is above
        # 0, so its STC freezes whenever MACD dips negative (and it ignores `tclength`, it reads `tc_length`)
        close = self.bars["Close"]
        macd = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
        smoothed_macd = _smoothed_stochastic(macd, tclength, factor)
        self.bars[column] = _smoothed_stochastic(smoothed_macd, tclength, factor)

        self.indicators["STC"] = Indicator(
            signal=IndicatorSignal(LONG=lambda x: x[column] > 50, SHORT=lambda x: x[column] < 50),
            columns=[column],
        )

    def add_commodity_channel_index(self, length: int, c: float) -> None:
        """
        CCI (Commodity Channel Index)
        https://www.tradingview.com/support/solutions/43000502001-commodity-channel-index-cci/
        https://www.investopedia.com/terms/c/commoditychannelindex.asp

        default: length=14, c=0.015

        The Commodity Channel Index (CCI) is a versatile indicator that can be used to identify a new trend or
        warn of extreme conditions. CCI measures the current price level relative to an average price level over
        a given period of time. Readings above +100 are considered overbought, and readings
        below -100 are considered oversold.
        """
        column = f"CCI_{length}_{c}"

        # Computed here: pandas_ta 0.4.71b0 drops the parentheses, typical - mean / (c * mad), so its CCI sits
        # far below -100 on any price level
        typical = (self.bars["High"] + self.bars["Low"] + self.bars["Close"]) / 3
        mean_deviation = typical.rolling(length).apply(lambda window: np.abs(window - window.mean()).mean(), raw=True)
        self.bars[column] = (typical - typical.rolling(length).mean()) / (c * mean_deviation)

        self.indicators["CCI"] = Indicator(
            signal=IndicatorSignal(LONG=lambda x: x[column] > 100, SHORT=lambda x: x[column] < -100),
            columns=[column],
        )

    def add_relative_vigor_index(self, length: int, length_swma: int, length_divergence: int) -> None:
        """
        RVGI (Relative Vigor Index)
        https://www.investopedia.com/terms/r/relative_vigor_index.asp

        default: length=14, length_swma=4

        The Relative Vigor Index attempts to measure the strength of a trend relative to
        its closing price to its trading range.  It is based on the belief that it tends
        to close higher than they open in uptrends or close lower than they open in
        downtrends.

        RVI Divergences: Divergence between the RVI indicator and price suggests there will be
        a near-term change in the trend in the direction of the RVI's trend. So, if a stock price is
        rising and the RVI indicator is falling, it predicts the stock will reverse over the near term.

        RVI Crossovers: Like many oscillators, the RVI has a signal line that's often calculated with
        price inputs. A crossover above the signal line is a bullish indicator, while a crossover below the
        signal line is a bearish indicator. These crossovers are designed to be leading indicators of
        future price direction.
        """
        rvgi_column = f"RVGI_{length}_{length_swma}"
        signal_column = f"RVGIs_{length}_{length_swma}"
        slope_column = "RVGI_slope"

        self.bars.ta.rvgi(length=length, swma_length=length_swma, append=True)
        if rvgi_column not in self.bars.columns:
            log.debug("Indicator 'Momentum -> RVGI' can not be added.")
            return

        close_slope_column = self._add_divergence_slopes(rvgi_column, slope_column, length_divergence)

        self.indicators["RVGI"] = Indicator(
            signal=IndicatorSignal(
                LONG=lambda x: (x[rvgi_column] > x[signal_column] and x[rvgi_column] > 0 and x[signal_column] > 0)
                or (x[slope_column] > 0 and x[close_slope_column] < 0),
                SHORT=lambda x: (x[rvgi_column] < x[signal_column] and x[rvgi_column] < 0 and x[signal_column] < 0)
                or (x[slope_column] < 0 and x[close_slope_column] > 0),
            ),
            columns=[rvgi_column, signal_column, slope_column, close_slope_column],
        )

    def add_macd_dema(self, length_fast: int, length_slow: int) -> None:
        """
        MACD-like indicator using 2 DEMA

        This looks like MACD but uses 2 DEMA instead of EMA.
        """
        fast_column, slow_column, macd_column = f"DEMA_{length_fast}", f"DEMA_{length_slow}", "MACD_DEMA"

        self.bars.ta.dema(length=length_fast, append=True)
        self.bars.ta.dema(length=length_slow, append=True)
        self.bars[macd_column] = self.bars[fast_column] - self.bars[slow_column]

        self.indicators["MACD_DEMA"] = Indicator(
            signal=IndicatorSignal(LONG=lambda x: x[macd_column] > 0, SHORT=lambda x: x[macd_column] < 0),
            columns=[macd_column],
        )

    def add_stochastic_oscillator(self, k: int, d: int, smooth_k: int, mamode: str) -> None:
        """
        STOCH (Stochastic Oscillator)
        https://www.investopedia.com/terms/s/stochasticoscillator.asp

        default: k=14, d=3, smooth_k=3, mamode="sma"

        The Stochastic Oscillator is a momentum indicator that shows the location of the close relative
        to the high-low range over a set number of periods. According to an interview with Lane, the
        Stochastic Oscillator "doesn't follow price, it doesn't follow volume or anything like that.
        It follows the speed or the momentum of price. As a rule, the momentum changes direction before price."
        """
        k_column, d_column = f"STOCHk_{k}_{d}_{smooth_k}", f"STOCHd_{k}_{d}_{smooth_k}"

        self.bars.ta.stoch(k=k, d=d, smooth_k=smooth_k, mamode=mamode, append=True)
        if k_column not in self.bars.columns:
            log.debug("Indicator 'Momentum -> STOCH' can not be added.")
            return

        self.indicators["STOCH"] = Indicator(
            signal=IndicatorSignal(
                LONG=lambda x: x[k_column] > x[d_column] and x[k_column] > 70 and x[d_column] > 70,
                SHORT=lambda x: x[k_column] < x[d_column] and x[k_column] < 30 and x[d_column] < 30,
            ),
            columns=[k_column, d_column],
        )


def _smoothed_stochastic(series: pd.Series, length: int, factor: float) -> pd.Series:
    """Stochastic of `series` over `length` bars (0-100, held where the window is flat), smoothed exponentially with
    weight `factor` on the newest value: one of the two STC stages."""
    lowest = series.rolling(length, min_periods=1).min()
    value_range = series.rolling(length, min_periods=1).max() - lowest
    stochastic = (100 * (series - lowest) / value_range.where(value_range > 0)).ffill().fillna(0)

    return stochastic.ewm(alpha=factor, adjust=False).mean()
