from typing import Dict

import pandas_ta as ta  # type: ignore

from services.ta.indicators.models import Indicator, Panel, Plot, Plots, Signal
from services.ta.indicators.models.category_base import IndicatorsCategoryBase
from utils.logger import get_logger

log = get_logger()


class Overlap(IndicatorsCategoryBase):
    def _add_2dema(self, length_short: int, length_long: int) -> None:
        # TODO: add plots

        """
        2DEMA (Trend direction by Double EMA)
        """

        column_names = {
            "DEMA_short": f"DEMA_{length_short}",
            "DEMA_long": f"DEMA_{length_long}",
            "2DEMA": "2DEMA",
        }

        self.data.ta.dema(length=length_short, append=True)
        self.data.ta.dema(length=length_long, append=True)
        self.data[column_names["2DEMA"]] = self.data.apply(
            lambda x: 1 if x[column_names["DEMA_short"]] >= x[column_names["DEMA_long"]] else -1,
            axis=1,
        )

        if column_names["2DEMA"] not in self.data.columns:
            log.debug("Indicator 'Overlap -> 2DEMA' can not be added.")
            return

        self._indicators["2DEMA"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_names["2DEMA"]] == 1,
                SELL=lambda x: x[column_names["2DEMA"]] == -1,
            ),
            columns=[column_names["2DEMA"]],
        )

    def _add_gann_high_low_activator(self, length_high: int, length_low: int, mamode: str) -> None:
        """
        GHLA (Gann High-Low Activator)
        https://www.sierrachart.com/index.php?page=doc/StudiesReference.php&ID=447&Name=Gann_HiLo_Activator
        https://www.tradingview.com/script/XNQSLIYb-Gann-High-Low/
        """

        column_name = f"HILO_{length_high}_{length_low}"

        self.data.ta.hilo(high_length=length_high, low_length=length_low, mamode=mamode, append=True)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Overlap -> GHLA' can not be added.")
            return

        self._indicators["GHLA"] = Indicator(
            signal=Signal(
                BUY=lambda x: x["Close"] > x[column_name],
                SELL=lambda x: x["Close"] < x[column_name],
            ),
            columns=[column_name],
            plots=Plots(
                panel=Panel.MAIN,
                list=[Plot(columns=[column_name], color="orange")],
            ),
        )

    def _add_linear_regression(self, length: int) -> None:
        """
        LINREG (Linear Regression)
        """

        column_name = f"LRr_{length}"

        self.data.ta.linreg(length=length, r=True, append=True)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Overlap -> LINREG' can not be added.")
            return

        self.data["LRr_direction"] = self.data[column_name].rolling(2).apply(lambda x: x.iloc[1] > x.iloc[0])

        self._indicators["LINREG"] = Indicator(
            signal=Signal(
                BUY=lambda x: x["LRr_direction"] == 1,
                SELL=lambda x: x["LRr_direction"] == 0,
            ),
            columns=["LRr_direction"],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_name], color="orange", ylabel="Overlap [LINREG]")],
            ),
        )

    def get(self) -> Dict:
        self._add_2dema(length_short=15, length_long=30)
        self._add_gann_high_low_activator(length_high=13, length_low=21, mamode="sma")
        self._add_linear_regression(length=14)

        return super().get()
