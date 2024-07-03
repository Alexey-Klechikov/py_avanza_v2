from typing import Dict

import pandas_ta as ta  # type: ignore

from services.ta.indicators.models import HorizontalLine, Indicator, IndicatorsCategoryBase, Panel, Plot, Plots, Signal
from utils.logger import get_logger

log = get_logger()


class Volatility(IndicatorsCategoryBase):
    def _add_starc_bands(self, length_sma: int, length_atr: int, multiplier_atr: float) -> None:
        # TODO: add plots
        """
        STARC (Stoller Average Range Channel)
        https://www.investopedia.com/terms/s/starc.asp
        """

        column_names = {
            "STARC_U": f"STARC_U_{length_sma}_{length_atr}_{multiplier_atr}",
            "STARC_B": f"STARC_B_{length_sma}_{length_atr}_{multiplier_atr}",
        }

        sma = self.data.ta.sma(length=length_sma)
        atr = self.data.ta.atr(length=length_atr)

        self.data[column_names["STARC_U"]] = sma + multiplier_atr * atr
        self.data[column_names["STARC_B"]] = sma - multiplier_atr * atr

        self._indicators["STARC"] = Indicator(
            signal=Signal(
                BUY=lambda x: x["Close"] < x[column_names["STARC_B"]],
                SELL=lambda x: x["Close"] > x[column_names["STARC_U"]],
            ),
            columns=list(column_names.values()),
        )

    def _add_mass_index(self, fast: int, slow: int) -> None:
        """
        MASSI (Mass Index)
        https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/mass-index#introduction
        """

        column_name = f"MASSI_{fast}_{slow}"

        self.data.ta.massi(fast=fast, slow=slow, append=True)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Volatility -> MASSI' can not be added.")
            return

        self._indicators["MASSI"] = Indicator(
            signal=Signal(
                BUY=lambda x: 26 < x[column_name] < 27,
                SELL=lambda x: 26 < x[column_name] < 27,
            ),
            columns=[column_name],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[
                    Plot(column=column_name, color="orange", ylabel="Volatility [MASSI]"),
                ],
                horizontal_lines=[
                    HorizontalLine(y=27, color="red"),
                    HorizontalLine(y=26, color="black"),
                    HorizontalLine(y=24, color="blue"),
                ],
            ),
        )

    def _add_holt_winter_channel(self, na: float, nb: float, nc: float, nd: float, scalar: float) -> None:
        """
        HWC (Holt-Winter Channel)
        https://www.mql5.com/en/code/20857
        """

        column_name = "HWM"

        self.data.ta.hwc(na=na, nb=nb, nc=nc, nd=nd, scalar=scalar, append=True)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Volatility -> HWC' can not be added.")
            return

        self._indicators["HWC"] = Indicator(
            signal=Signal(
                BUY=lambda x: x["Close"] > x[column_name],
                SELL=lambda x: x["Close"] < x[column_name],
            ),
            columns=[column_name],
            plots=Plots(
                panel=Panel.MAIN,
                list=[
                    Plot(column=column_name, color="brown", ylabel="Volatility [HWC]"),
                ],
            ),
        )

    def _add_bollinger_bands(self, length: int, std: float) -> None:
        """
        BBANDS (Bollinger Bands)
        """
        column_names = {"BBL": f"BBL_{length}_{std}", "BBU": f"BBU_{length}_{std}"}

        self.data.ta.bbands(length=length, std=std, append=True)
        if column_names["BBL"] not in self.data.columns:
            log.debug("Indicator 'Volatility -> BBANDS' can not be added.")
            return

        self._indicators["BBANDS"] = Indicator(
            signal=Signal(
                BUY=lambda x: x["Close"] > x[column_names["BBL"]],
                SELL=lambda x: x["Close"] < x[column_names["BBU"]],
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.MAIN,
                list=[
                    Plot(column=column_names["BBL"], color="brown", ylabel="Volatility [BBANDS]"),
                    Plot(column=column_names["BBU"], color="brown", secondary_y=False),
                ],
            ),
        )

    def _add_acceleration_bands(self, length: int, c: int, mamode: str) -> None:
        # TODO: double-check this indicator
        # TODO: add plots
        """
        ACCBANDS (Acceleration Bands)
        https://trendspider.com/learning-center/getting-started-with-acceleration-bands-in-technical-analysis/
        """

        column_names = {
            "ACCBU": f"ACCBU_{length}",
            "ACCBM": f"ACCBM_{length}",
            "ACCBL": f"ACCBL_{length}",
        }

        self.data.ta.accbands(length=length, c=c, mamode=mamode, append=True)
        if column_names["ACCBM"] not in self.data.columns:
            log.debug("Indicator 'Volatility -> ACCBANDS' can not be added.")
            return

        self._indicators["ACCBANDS"] = Indicator(
            signal=Signal(
                BUY=lambda x: x["Close"] > x[column_names["ACCBM"]],
                SELL=lambda x: x["Close"] < x[column_names["ACCBM"]],
            ),
            columns=list(column_names.values()),
        )

    def get(self) -> Dict:
        self._add_starc_bands(length_sma=6, length_atr=14, multiplier_atr=1.5)
        self._add_mass_index(fast=9, slow=25)
        self._add_holt_winter_channel(na=0.2, nb=0.1, nc=0.1, nd=0.1, scalar=1)
        self._add_bollinger_bands(length=20, std=2.0)
        self._add_acceleration_bands(length=20, c=4, mamode="sma")

        return super().get()


#     # Volatility
#     @staticmethod
#     def starc_bands(
#         data: pd.DataFrame, length_sma: int, length_atr: int, multiplier_atr: float
#     ):
#         """https://www.investopedia.com/terms/s/starc.asp"""

#         make_name = lambda x: f"{x}_{length_sma}_{length_atr}_{multiplier_atr}"

#         sma = data.ta.sma(length=length_sma)
#         atr = data.ta.atr(length=length_atr)

#         data[make_name("STARC_U")] = sma + multiplier_atr * atr
#         data[make_name("STARC_B")] = sma - multiplier_atr * atr

#         return data
