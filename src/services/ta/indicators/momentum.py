import pandas_ta as ta  # type: ignore

from services.ta.indicators.models import HorizontalLine, Indicator, Panel, Plot, Plots, Signal
from services.ta.indicators.models.category_base import IndicatorsCategoryBase
from utils.logger import get_logger

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

        column_name = f"STC_{tclength}_{fast}_{slow}_{factor}"

        self.data.ta.stc(tclength=tclength, fast=fast, slow=slow, factor=factor, append=True)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Momentum -> STC' can not be added.")
            return

        self.indicators["STC"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_name] > 75,
                SELL=lambda x: x[column_name] < 25,
            ),
            columns=[column_name],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_name], color="orange", ylim=[-10, 110], ylabel="Momentum [STC]")],
                horizontal_lines=[HorizontalLine(y=25, color="red"), HorizontalLine(y=75, color="blue")],
            ),
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

        column_name = f"CCI_{length}_{c}"

        self.data.ta.cci(length=length, c=c, append=True)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Momentum -> CCI' can not be added.")
            return

        self.indicators["CCI"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_name] > 100,
                SELL=lambda x: x[column_name] < -100,
            ),
            columns=[column_name],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_name], ylabel="Momentum [CCI]")],
                horizontal_lines=[HorizontalLine(y=100, color="red"), HorizontalLine(y=-100, color="blue")],
            ),
        )

    def add_relative_vigor_index(self, length: int, length_swma: int) -> None:
        """
        RVGI (Relative Vigor Index)
        https://www.investopedia.com/terms/r/relative_vigor_index.asp

        default: length=14, length_swma=4

        The Relative Vigor Index attempts to measure the strength of a trend relative to
        its closing price to its trading range.  It is based on the belief that it tends
        to close higher than they open in uptrends or close lower than they open in
        downtrends.
        """

        column_names = {
            "RVGI": f"RVGI_{length}_{length_swma}",
            "RVGIs": f"RVGIs_{length}_{length_swma}",
        }

        self.data.ta.rvgi(length=length, swma_length=length_swma, append=True)
        if column_names["RVGI"] not in self.data.columns:
            log.debug("Indicator 'Momentum -> RVGI' can not be added.")
            return

        self.indicators["RVGI"] = Indicator(
            signal=Signal(
                BUY=lambda x: all(
                    [
                        x[column_names["RVGI"]] > x[column_names["RVGIs"]],
                        x[column_names["RVGI"]] > 0,
                        x[column_names["RVGIs"]] > 0,
                    ],
                ),
                SELL=lambda x: all(
                    [
                        x[column_names["RVGI"]] < x[column_names["RVGIs"]],
                        x[column_names["RVGI"]] < 0,
                        x[column_names["RVGIs"]] < 0,
                    ],
                ),
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=list(column_names.values()), ylabel="Momentum [RVGI]")],
                horizontal_lines=[HorizontalLine(y=0, color="red")],
            ),
        )

    def add_macd_dema(self, length_fast: int, length_slow: int) -> None:
        """
        MACD-like indicator using 2 DEMA

        This looks like MACD but uses 2 DEMA instead of EMA.
        """

        column_names = {
            "DEMA_fast": f"DEMA_{length_fast}",
            "DEMA_slow": f"DEMA_{length_slow}",
            "MACD_DEMA": "MACD_DEMA",
        }

        self.data.ta.dema(length=length_fast, append=True)
        self.data.ta.dema(length=length_slow, append=True)
        self.data[column_names["MACD_DEMA"]] = self.data.apply(
            lambda x: x[column_names["DEMA_fast"]] - x[column_names["DEMA_slow"]],
            axis=1,
        )

        if column_names["MACD_DEMA"] not in self.data.columns:
            log.debug("Indicator 'Momentum -> MACD_DEMA' can not be added.")
            return

        self.indicators["MACD_DEMA"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_names["MACD_DEMA"]] > 0,
                SELL=lambda x: x[column_names["MACD_DEMA"]] < 0,
            ),
            columns=[column_names["MACD_DEMA"]],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_names["MACD_DEMA"]], ylabel="Momentum [MACD_DEMA]")],
                horizontal_lines=[HorizontalLine(y=0, color="red")],
            ),
        )

    def add_stochastic_oscillator(self, k: int, d: int, smooth_k: int, mamode: str) -> None:
        """
        STOCH (Stochastic Oscillator)
        https://www.investopedia.com/terms/s/stochasticoscillator.asp

        default: k=14, d=3, smooth_k=3, mamode="sma"

        The Stochastic Oscillator is a momentum indicator that shows the location of the close relative to the high-low
        range over a set number of periods. According to an interview with Lane, the Stochastic Oscillator "doesn't follow
        price, it doesn't follow volume or anything like that. It follows the speed or the momentum of price. As a rule,
        the momentum changes direction before price."
        """

        column_names = {
            "STOCHk": f"STOCHk_{k}_{d}_{smooth_k}",
            "STOCHd": f"STOCHd_{k}_{d}_{smooth_k}",
        }

        self.data.ta.stoch(k=k, d=d, smooth_k=smooth_k, mamode=mamode, append=True)
        if column_names["STOCHk"] not in self.data.columns:
            log.debug("Indicator 'Momentum -> STOCH' can not be added.")
            return

        self.indicators["STOCH"] = Indicator(
            signal=Signal(
                BUY=lambda x: all(
                    [
                        x[column_names["STOCHk"]] > x[column_names["STOCHd"]],
                        x[column_names["STOCHk"]] > 60,
                        x[column_names["STOCHd"]] > 60,
                    ],
                ),
                SELL=lambda x: all(
                    [
                        x[column_names["STOCHk"]] < x[column_names["STOCHd"]],
                        x[column_names["STOCHk"]] < 40,
                        x[column_names["STOCHd"]] < 40,
                    ],
                ),
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=list(column_names.values()), ylabel="Momentum [STOCH]")],
                horizontal_lines=[HorizontalLine(y=60, color="red"), HorizontalLine(y=40, color="blue")],
            ),
        )


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
