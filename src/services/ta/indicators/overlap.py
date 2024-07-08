import pandas_ta as ta  # type: ignore

from services.ta.indicators.models import HorizontalLine, Indicator, Panel, Plot, Plots, Signal
from services.ta.indicators.models.category_base import IndicatorsCategoryBase
from utils.logger import get_logger

log = get_logger()


class Overlap(IndicatorsCategoryBase):
    def add_gann_high_low_activator(self, length_high: int, length_low: int, mamode: str) -> None:
        """
        GHLA (Gann High-Low Activator)
        https://www.sierrachart.com/index.php?page=doc/StudiesReference.php&ID=447&Name=Gann_HiLo_Activator
        https://www.tradingview.com/script/XNQSLIYb-Gann-High-Low/

        default: high_length=13, low_length=21, mamode="sma"

        The Gann High Low Activator Indicator was created by Robert Krausz in a 1998
        issue of Stocks & Commodities Magazine. It is a moving average based trend
        indicator consisting of two different simple moving averages.

        The indicator tracks both curves (of the highs and the lows). The close of the
        bar defines which of the two gets plotted.
        """

        column_name = f"HILO_{length_high}_{length_low}"

        self.data.ta.hilo(high_length=length_high, low_length=length_low, mamode=mamode, append=True)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Overlap -> GHLA' can not be added.")
            return

        self.indicators["GHLA"] = Indicator(
            signal=Signal(
                LONG=lambda x: x["Close"] > x[column_name],
                SHORT=lambda x: x["Close"] < x[column_name],
            ),
            columns=[column_name],
            plots=Plots(
                panel=Panel.MAIN,
                list=[Plot(columns=[column_name], color="orange", ylabel="Overlap [GHLA]")],
            ),
        )

    def add_linear_regression(self, length: int) -> None:
        """
        LINREG (Linear Regression)

        default: length=14

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
                LONG=lambda x: x[column_name] > 0.1,
                SHORT=lambda x: x[column_name] < -0.1,
            ),
            columns=[column_name],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_name], color="orange", ylabel="Overlap [LINREG]")],
                horizontal_lines=[HorizontalLine(y=0, color="red")],
            ),
        )
