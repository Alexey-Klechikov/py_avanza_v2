import pandas_ta as ta  # pylint: disable=unused-import # noqa: F401

from services.ta.indicators.models.category_base import IndicatorsCategoryBase
from services.ta.indicators.models.indicator import Indicator, IndicatorSignal
from utils.logger.operators import get_logger

log = get_logger()


class Overlap(IndicatorsCategoryBase):
    def add_linear_regression(self, length: int, limit: float) -> None:
        """
        LINREG (Linear Regression Correlation)

        default: length=14, limit=0.1

        Linear Regression Moving Average (LINREG). This is a simplified version of a
        Standard Linear Regression. LINREG is a rolling regression of one variable. A
        Standard Linear Regression is between two or more variables.
        """
        column = f"LINREGr_{length}"

        self.bars.ta.linreg(length=length, r=True, append=True)
        if column not in self.bars.columns:
            log.debug("Indicator 'Overlap -> LINREG' can not be added.")
            return

        self.indicators["LINREG"] = Indicator(
            signal=IndicatorSignal(LONG=lambda x: x[column] > limit, SHORT=lambda x: x[column] < -limit),
            columns=[column],
        )

    def add_slope(self, length: int, limit: float) -> None:
        """
        SLOPE (Linear Regression Slope)

        default: length=14, limit=0.1

        Linear Regression Moving Average (LINREG). This is a simplified version of a
        Standard Linear Regression. LINREG is a rolling regression of one variable. A
        Standard Linear Regression is between two or more variables.
        """
        column = f"LINREGm_{length}"

        self.bars.ta.linreg(length=length, slope=True, append=True)
        if column not in self.bars.columns:
            log.debug("Indicator 'Overlap -> SLOPE' can not be added.")
            return

        self.indicators["SLOPE"] = Indicator(
            signal=IndicatorSignal(LONG=lambda x: x[column] > limit, SHORT=lambda x: x[column] < -limit),
            columns=[column],
        )

    def add_supertrend(self, length: int, multiplier: float) -> None:
        """
        SUPERTREND (SuperTrend)
        https://trendspider.com/learning-center/supertrend-indicator-a-comprehensive-guide/

        default: length=7, multiplier=3.0

        It is used to identify market trends and potential entry and exit points in trading.
        The indicator is based on two dynamic values, period and multiplier, and incorporates
        the concept of Average True Range (ATR) to measure market volatility. The SuperTrend
        Indicator generates buy and sell signals by plotting a line on the price chart.
        """
        long_column = f"SUPERTl_{length}_{multiplier}"
        short_column = f"SUPERTs_{length}_{multiplier}"

        self.bars.ta.supertrend(length=length, multiplier=multiplier, append=True)
        if long_column not in self.bars.columns:
            log.debug("Indicator 'Overlap -> SUPERTREND' can not be added.")
            return

        self.indicators["SUPERTREND"] = Indicator(
            signal=IndicatorSignal(
                LONG=lambda x: x["Close"] > x[long_column],
                SHORT=lambda x: x["Close"] < x[short_column],
            ),
            columns=[long_column, short_column],
        )
