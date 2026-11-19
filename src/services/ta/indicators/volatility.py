import pandas_ta as ta  # pylint: disable=unused-import # noqa: F401
from pandas_ta.overlap import wma

from services.ta.indicators.models.category_base import IndicatorsCategoryBase
from services.ta.indicators.models.indicator import Indicator, IndicatorSignal
from utils.logger.operators import get_logger

log = get_logger()


class Volatility(IndicatorsCategoryBase):
    def add_starc_bands(self, length_ma: int, length_atr: int, multiplier_atr: float) -> None:
        """
        STARC (Stoller Average Range Channel)
        https://www.investopedia.com/terms/s/starc.asp
        https://www.viperreport.com/how-to-use-starc-bands-one-of-my-favorite-chart-tools-of-all-time/

        defaults: length_ma = 6, length_atr = 15 , multiplier_atr = 2

        During an overall uptrend, buying near the lower band and selling near the top band is favorable,
        for example. STARC bands can provide insight for both ranging and trending markets.
        """
        lower_column = f"STARC_B_{length_ma}_{length_atr}_{multiplier_atr}"
        upper_column = f"STARC_U_{length_ma}_{length_atr}_{multiplier_atr}"

        moving_average = wma(self.bars["Close"], length=length_ma)
        band_width = multiplier_atr * self.bars.ta.atr(length=length_atr)
        self.bars[lower_column] = moving_average - band_width
        self.bars[upper_column] = moving_average + band_width

        self.indicators["STARC"] = Indicator(
            signal=IndicatorSignal(
                LONG=lambda x: x["High"] > x[upper_column],
                SHORT=lambda x: x["Low"] < x[lower_column],
            ),
            columns=[lower_column, upper_column],
        )

    def add_bollinger_bands(self, length: int, std: float) -> None:
        """
        BBANDS (Bollinger Bands)
        https://www.investopedia.com/terms/b/bollingerbands.asp

        defaults: length = 20, std = 2.0

        The bands widen when a stock's price becomes more volatile and contract when it is more stable.
        Many traders see stocks as overbought as their price nears the upper band and oversold as they
        approach the lower band, signaling an opportune time to trade.
        """
        middle_column = f"BBM_{length}_{std}_{std}"
        lower_column = f"BBL_{length}_{std}_{std}"
        upper_column = f"BBU_{length}_{std}_{std}"

        self.bars.ta.bbands(length=length, lower_std=std, upper_std=std, append=True)
        if middle_column not in self.bars.columns:
            log.debug("Indicator 'Volatility -> BBANDS' can not be added.")
            return

        self.indicators["BBANDS"] = Indicator(
            signal=IndicatorSignal(
                LONG=lambda x: x["Close"] > x[upper_column],
                SHORT=lambda x: x["Close"] < x[lower_column],
            ),
            columns=[middle_column, lower_column, upper_column],
        )

    def add_acceleration_bands(self, length: int, c: int, mamode: str) -> None:
        """
        ACCBANDS (Acceleration Bands)
        https://trendspider.com/learning-center/getting-started-with-acceleration-bands-in-technical-analysis/

        defaults: length = 20, c = 4, mamode = "sma"

        When the price is above the midpoint, it indicates a bullish trend, while a price below the middle signals
        a bearish trend.
        Breakout traders use Acceleration Bands to identify potential breakouts from a consolidation phase. When
        the price moves above the upper band or below the lower band, it may signify a breakout, signaling a
        possible entry or exit point for traders.
        Depending on the market trend, the upper and lower bands can provide potential support or resistance.
        In a bullish trend, the lower band may serve as support, while the upper band may act as resistance in
        a bearish trend. Traders can use these levels to set stop-loss orders or profit targets.
        """
        upper_column, middle_column, lower_column = f"ACCBU_{length}", f"ACCBM_{length}", f"ACCBL_{length}"

        self.bars.ta.accbands(length=length, c=c, mamode=mamode, append=True)
        if middle_column not in self.bars.columns:
            log.debug("Indicator 'Volatility -> ACCBANDS' can not be added.")
            return

        self.indicators["ACCBANDS"] = Indicator(
            signal=IndicatorSignal(
                LONG=lambda x: x["Close"] > x[upper_column],
                SHORT=lambda x: x["Close"] < x[lower_column],
            ),
            columns=[upper_column, middle_column, lower_column],
        )
