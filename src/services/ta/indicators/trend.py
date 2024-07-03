from typing import Dict

import pandas_ta as ta  # type: ignore

from services.ta.indicators.models import HorizontalLine, Indicator, IndicatorsCategoryBase, Panel, Plot, Plots, Signal
from utils.logger import get_logger

log = get_logger()


class Trend(IndicatorsCategoryBase):
    def _add_trend_intensity_index(self, length_sma: int, length_signal: int) -> None:
        # TODO: double-check this indicator
        # TODO: add plots
        """
        TII (Trend Intensity Index)
        https://raposa.trade/blog/4-ways-to-trade-the-trend-intensity-indicator/
        """

        column_names = {
            "TII": f"TII_{length_sma}_{length_signal}",
            "TII_SIGNAL": f"TII_SIGNAL_{length_sma}_{length_signal}",
        }

        sma = self.data.ta.sma(length=length_sma)
        diff = self.data["Close"] - sma
        pos_count = diff.map(lambda x: 1 if x > 0 else 0).rolling(int(length_sma / 2)).sum()
        self.data[column_names["TII"]] = 200 * (pos_count) / length_sma
        self.data[column_names["TII_SIGNAL"]] = self.data.ta.ema(
            close=self.data[column_names["TII"]],
            length=length_signal,
        )

        self._indicators["TII"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_names["TII_SIGNAL"]] > x[column_names["TII"]],
                SELL=lambda x: x[column_names["TII_SIGNAL"]] < x[column_names["TII"]],
            ),
            columns=list(column_names.values()),
        )

    def _add_trend_based_on_ttm_squeeze(self, length: int) -> None:
        # TODO: add plots
        """
        TTM_TREND (Trend based on TTM Squeeze)
        """

        column_name = f"TTM_TRND_{length}"

        self.data.ta.ttm_trend(length=length, append=True)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Trend -> TTM_TREND' can not be added.")
            return

        self._indicators["TTM_TREND"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_name] == 1,
                SELL=lambda x: x[column_name] == -1,
            ),
            columns=[column_name],
        )

    def _add_vertical_horizontal_filter(self, length: int, length_ema: int) -> None:
        # TODO: add plots
        """
        VHF (Vertical Horizontal Filter)
        """

        column_name = f"VHF_{length}_EMA_{length_ema}"

        self.data[column_name] = self.data.ta.ema(
            close=self.data.ta.vhf(length=length),
            length=length_ema,
        )
        if column_name not in self.data.columns:
            log.debug("Indicator 'Trend -> VHF' can not be added.")
            return

        self._indicators["VHF"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_name] > 0.45,
                SELL=lambda x: x[column_name] > 0.4,
            ),
            columns=[column_name],
        )

    def _add_vortex_indicator(self, length: int) -> None:
        # TODO: add plots
        """
        VORTEX (Vortex Indicator)
        """

        column_names = {
            "VTXP": f"VTXP_{length}",
            "VTXM": f"VTXM_{length}",
        }

        self.data.ta.vortex(length=length, append=True)
        if column_names["VTXP"] not in self.data.columns:
            log.debug("Indicator 'Trend -> VORTEX' can not be added.")
            return

        self._indicators["VORTEX"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_names["VTXP"]] > x[column_names["VTXM"]],
                SELL=lambda x: x[column_names["VTXM"]] < x[column_names["VTXP"]],
            ),
            columns=list(column_names.values()),
        )

    def _add_parabolic_stop_and_reverse(self, acceleration: float, maximum: float) -> None:
        """
        PSAR (Parabolic Stop and Reverse)
        """

        column_names = {
            "PSARl": f"PSARl_{acceleration}_{maximum}",
            "PSARs": f"PSARs_{acceleration}_{maximum}",
        }

        self.data.ta.psar(af=acceleration, max_af=maximum, append=True)
        if column_names["PSARl"] not in self.data.columns:
            log.debug("Indicator 'Trend -> PSAR' can not be added.")
            return

        self._indicators["PSAR"] = Indicator(
            signal=Signal(
                BUY=lambda x: x["Close"] > x[column_names["PSARl"]],
                SELL=lambda x: x["Close"] < x[column_names["PSARs"]],
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.MAIN,
                list=[
                    Plot(
                        column=column_names["PSARl"],
                        color="navy",
                        type="scatter",
                        markersize=10,
                        ylabel="Trend [PSAR]",
                    ),
                    Plot(column=column_names["PSARs"], color="navy", type="scatter", markersize=10, secondary_y=False),
                ],
            ),
        )

    def _add_choppiness_index(self, length: int, length_atr: int, scalar: float) -> None:
        """
        CHOP (Choppiness Index)
        """

        column_name = f"CHOP_{length}_{length_atr}_{scalar}"

        self.data.ta.chop(length=length, atr_length=length_atr, scalar=scalar, append=True)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Trend -> CHOP' can not be added.")
            return

        self._indicators["CHOP"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_name] < 61.8,
                SELL=lambda x: x[column_name] > 61.8,
            ),
            columns=[column_name],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[
                    Plot(column=column_name, color="orange", ylim=[0, 100], ylabel="Trend [CHOP]"),
                ],
                horizontal_lines=[
                    HorizontalLine(y=60, color="red"),
                    HorizontalLine(y=40, color="blue"),
                ],
            ),
        )

    def _add_chande_kroll_stop(self, p: int, x: float, q: int) -> None:
        """
        CKSP (Chande Kroll Stop)

        p (int): ATR and first stop period.
        x (float): ATR scalar.
        q (int): Second stop period.

        # TODO: try p=10, x=1, q=9
        """

        column_names = {
            "CKSPl": f"CKSPl_{p}_{x}_{q}",
            "CKSPs": f"CKSPs_{p}_{x}_{q}",
        }

        self.data.ta.cksp(p=p, x=x, q=q, append=True)
        if column_names["CKSPl"] not in self.data.columns:
            log.debug("Indicator 'Trend -> CKSP' can not be added.")
            return

        plot_lim = [
            min([self.data[i].min() for i in column_names.values()]),
            max([self.data[i].max() for i in column_names.values()]),
        ]

        self._indicators["CKSP"] = Indicator(
            signal=Signal(
                BUY=lambda x: x["Close"] > x[column_names["CKSPl"]],
                SELL=lambda x: x["Close"] < x[column_names["CKSPs"]],
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[
                    Plot(column=column_names["CKSPl"], color="orange", ylim=plot_lim, ylabel="Trend [CKSP]"),
                    Plot(column=column_names["CKSPs"], color="black", ylim=plot_lim, secondary_y=False),
                ],
            ),
        )

    def get(self) -> Dict[str, Indicator]:
        self._add_trend_intensity_index(length_sma=15, length_signal=5)
        self._add_trend_based_on_ttm_squeeze(length=8)
        self._add_vertical_horizontal_filter(length=30, length_ema=10)
        self._add_vortex_indicator(length=14)
        self._add_parabolic_stop_and_reverse(acceleration=0.02, maximum=0.2)
        self._add_choppiness_index(length=14, length_atr=1, scalar=100.0)
        self._add_chande_kroll_stop(p=10, x=3.0, q=20)

        return super().get()
