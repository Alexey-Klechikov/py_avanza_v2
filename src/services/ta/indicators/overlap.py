import pandas_ta as ta  # type: ignore

from services.ta.indicators.models import HorizontalLine, Indicator, Panel, Plot, Plots, Signal
from services.ta.indicators.models.category_base import IndicatorsCategoryBase
from utils.logger import get_logger

log = get_logger()


class Overlap(IndicatorsCategoryBase):
    def add_linear_regression(self, length: int, limit: float) -> None:
        """
        LINREG (Linear Regression)

        default: length=14, limit=0.1

        Linear Regression Moving Average (LINREG). This is a simplified version of a
        Standard Linear Regression. LINREG is a rolling regression of one variable. A
        Standard Linear Regression is between two or more variables.
        """

        column_name = f"LRr_{length}"

        self.data.ta.linreg(length=length, r=True, append=True)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Overlap -> LINREG' can not be added.")
            return

        self.indicators["LINREG"] = Indicator(
            signal=Signal(
                LONG=lambda x: x[column_name] > limit,
                SHORT=lambda x: x[column_name] < -1 * limit,
            ),
            columns=[column_name],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_name], color="orange", ylabel="Overlap [LINREG]")],
                horizontal_lines=[HorizontalLine(y=0, color="red")],
            ),
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

        column_names = {
            # "SUPERTREND": f"SUPERT_{length}_{multiplier}",
            # "SUPERTREND_dir": f"SUPERTd_{length}_{multiplier}",
            "SUPERTREND_long": f"SUPERTl_{length}_{multiplier}",
            "SUPERTREND_short": f"SUPERTs_{length}_{multiplier}",
        }

        self.data.ta.supertrend(length=length, multiplier=multiplier, append=True)

        if column_names["SUPERTREND_long"] not in self.data.columns:
            log.debug("Indicator 'Overlap -> SUPERTREND' can not be added.")
            return

        self.indicators["SUPERTREND"] = Indicator(
            signal=Signal(
                LONG=lambda x: x["Close"] > x[column_names["SUPERTREND_long"]],
                SHORT=lambda x: x["Close"] < x[column_names["SUPERTREND_short"]],
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.MAIN,
                list=[Plot(columns=list(column_names.values()), ylabel="Overlap [SUPERTREND]")],
            ),
        )
