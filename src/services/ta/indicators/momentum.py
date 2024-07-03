from typing import Dict

import pandas_ta as ta  # type: ignore

from services.ta.indicators.models import HorizontalLine, Indicator, Panel, Plot, Plots, Signal
from services.ta.indicators.models.category_base import IndicatorsCategoryBase
from utils.logger import get_logger

log = get_logger()


class Momentum(IndicatorsCategoryBase):
    def _add_schaff_trend_cycle(self, tclength: int, fast: int, slow: int, factor: float) -> None:
        """
        STC (Schaff Trend Cycle)
        https://www.prorealcode.com/prorealtime-indicators/schaff-trend-cycle2/
        """

        column_name = f"STC_{tclength}_{fast}_{slow}_{factor}"

        self.data.ta.stc(tclength=tclength, fast=fast, slow=slow, factor=factor, append=True)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Momentum -> STC' can not be added.")
            return

        self._indicators["STC"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_name] < 75,
                SELL=lambda x: x[column_name] > 25,
            ),
            columns=[column_name],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_name], color="orange", ylim=[-10, 110], ylabel="Momentum [STC]")],
                horizontal_lines=[HorizontalLine(y=25, color="red"), HorizontalLine(y=75, color="blue")],
            ),
        )

    def _add_ultimate_oscillator(
        self,
        fast: int,
        medium: int,
        slow: int,
        fast_weight: float,
        medium_weight: float,
        slow_weight: float,
    ) -> None:
        """
        UO (Ultimate Oscillator)
        https://www.tradingview.com/support/solutions/43000502328-ultimate-oscillator-uo/
        """

        column_name = f"UO_{fast}_{medium}_{slow}"

        self.data.ta.uo(
            fast=fast,
            medium=medium,
            slow=slow,
            fast_w=fast_weight,
            medium_w=medium_weight,
            slow_w=slow_weight,
            append=True,
        )
        if column_name not in self.data.columns:
            log.debug("Indicator 'Momentum -> UO' can not be added.")
            return

        self._indicators["UO"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_name] < 30,
                SELL=lambda x: x[column_name] > 65,
            ),
            columns=[column_name],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_name], color="orange", ylim=[0, 100], ylabel="Momentum [UO]")],
                horizontal_lines=[HorizontalLine(y=65, color="red"), HorizontalLine(y=30, color="blue")],
            ),
        )

    def _add_commodity_channel_index(self, length: int, c: float) -> None:
        """
        CCI (Commodity Channel Index)
        https://www.tradingview.com/support/solutions/43000502001-commodity-channel-index-cci/
        """

        column_name = f"CCI_{length}_{c}"

        self.data.ta.cci(length=length, c=c, append=True)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Momentum -> CCI' can not be added.")
            return

        self.data["CCI_direction"] = self.data[column_name].rolling(2).apply(lambda x: x.iloc[1] > x.iloc[0])

        self._indicators["CCI"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_name] < -100 and x["CCI_direction"] == 1,
                SELL=lambda x: x[column_name] > 100 and x["CCI_direction"] == 0,
            ),
            columns=[column_name, "CCI_direction"],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_name], color="orange", ylabel="Momentum [CCI]")],
            ),
        )

    def _add_relative_vigor_index(self, length: int, length_swma: int) -> None:
        """
        RVGI (Relative Vigor Index)
        https://www.investopedia.com/terms/r/relative_vigor_index.asp
        """

        column_names = {
            "RVGI": f"RVGI_{length}_{length_swma}",
            "RVGIs": f"RVGIs_{length}_{length_swma}",
        }

        self.data.ta.rvgi(length=length, swma_length=length_swma, append=True)
        if column_names["RVGI"] not in self.data.columns:
            log.debug("Indicator 'Momentum -> RVGI' can not be added.")
            return

        self._indicators["RVGI"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_names["RVGI"]] > x[column_names["RVGIs"]],
                SELL=lambda x: x[column_names["RVGI"]] < x[column_names["RVGIs"]],
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_names["RVGI"], column_names["RVGIs"]], ylabel="Momentum [RVGI]")],
            ),
        )

    def _add_macd(self, fast: int, slow: int, signal: int) -> None:
        """
        MACD (Moving Average Convergence Divergence)
        """

        column_names = {
            "MACD": f"MACD_{fast}_{slow}_{signal}",
            "MACDh": f"MACDh_{fast}_{slow}_{signal}",
            "MACDs": f"MACDs_{fast}_{slow}_{signal}",
        }

        self.data.ta.macd(fast=fast, slow=slow, signal=signal, append=True)
        if column_names["MACD"] not in self.data.columns:
            log.debug("Indicator 'Momentum -> MACD' can not be added.")
            return

        self.data["MACD_ma_diff"] = self.data[column_names["MACDh"]].rolling(2).apply(lambda x: x.iloc[1] > x.iloc[0])

        self._indicators["MACD"] = Indicator(
            signal=Signal(
                BUY=lambda x: x["MACD_ma_diff"] == 1,
                SELL=lambda x: x["MACD_ma_diff"] == 0,
            ),
            columns=[column_names["MACD"], "MACD_ma_diff"],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_names["MACD"]], color="orange", ylim=[-0.1, 1.1], ylabel="Momentum [MACD]")],
            ),
        )

    def _add_stochastic_oscillator(self, k: int, d: int, smooth_k: int, mamode: str) -> None:
        """
        STOCH (Stochastic Oscillator)
        """

        column_names = {
            "STOCHk": f"STOCHk_{k}_{d}_{smooth_k}",
            "STOCHd": f"STOCHd_{k}_{d}_{smooth_k}",
        }

        self.data.ta.stoch(k=k, d=d, smooth_k=smooth_k, mamode=mamode, append=True)
        if column_names["STOCHk"] not in self.data.columns:
            log.debug("Indicator 'Momentum -> STOCH' can not be added.")
            return

        self._indicators["STOCH"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_names["STOCHd"]] < 80 and x[column_names["STOCHk"]] < 80,
                SELL=lambda x: x[column_names["STOCHd"]] > 20 and x[column_names["STOCHk"]] > 20,
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_names["STOCHk"], column_names["STOCHd"]], ylabel="Momentum [STOCH]")],
                horizontal_lines=[HorizontalLine(y=80, color="red"), HorizontalLine(y=20, color="blue")],
            ),
        )

    def get(self) -> Dict:
        self._add_schaff_trend_cycle(tclength=10, fast=12, slow=26, factor=0.5)
        self._add_ultimate_oscillator(fast=10, medium=15, slow=30, fast_weight=4.0, medium_weight=2.0, slow_weight=1.0)
        self._add_commodity_channel_index(length=14, c=0.015)
        self._add_relative_vigor_index(length=14, length_swma=4)
        self._add_macd(fast=8, slow=21, signal=5)
        self._add_stochastic_oscillator(k=14, d=3, smooth_k=3, mamode="sma")

        return super().get()


#     # Momentum
#     @staticmethod
#     def impulse_macd(
#         data: pd.DataFrame, length_ma: int, length_signal: int
#     ) -> pd.DataFrame:
#         """https://www.tradingview.com/script/qt6xLfLi-Impulse-MACD-LazyBear/"""

#         make_name = lambda x: f"{x}_{length_ma}_{length_signal}"

#         def _smooth_simple_moving_average(src, length):
#             ssma = np.full(len(src), np.nan)
#             ssma[0] = src[:length].mean()

#             for i in range(1, len(src)):
#                 ssma[i] = (ssma[i - 1] * (length - 1) + src[i]) / length

#             return ssma

#         def _zero_lag_exponential_moving_average(src, length):
#             ema1 = pd.Series(src).ewm(span=length).mean()
#             ema2 = ema1.ewm(span=length).mean()
#             d = ema1 - ema2

#             return ema1 + d

#         high_smooth = _smooth_simple_moving_average(data["High"], length_ma)
#         low_smooth = _smooth_simple_moving_average(data["Low"], length_ma)

#         mean_price = data[["High", "Low", "Close"]].mean(axis=1)
#         mean_zlema = _zero_lag_exponential_moving_average(mean_price, length_ma)

#         data[make_name("IMPULSE")] = np.where(
#             mean_zlema > high_smooth,
#             mean_zlema - high_smooth,
#             np.where(mean_zlema < low_smooth, mean_zlema - low_smooth, 0),
#         )

#         data[make_name("SIGNAL")] = (
#             pd.Series(data[make_name("IMPULSE")]).rolling(length_signal).mean()
#         )

#         return data
