import pandas_ta as ta  # type: ignore

from services.ta.indicators.models import HorizontalLine, Indicator, Panel, Plot, Plots, Signal
from services.ta.indicators.models.category_base import IndicatorsCategoryBase
from utils.logger import get_logger

log = get_logger()


class Volatility(IndicatorsCategoryBase):
    def add_starc_bands(self, length_sma: int, length_atr: int, multiplier_atr: float) -> None:
        """
        STARC (Stoller Average Range Channel)
        https://www.investopedia.com/terms/s/starc.asp
        https://www.viperreport.com/how-to-use-starc-bands-one-of-my-favorite-chart-tools-of-all-time/

        defaults: length_sma = 6, length_atr = 15 , multiplier_atr = 2

        During an overall uptrend, buying near the lower band and selling near the top band is favorable,
        for example. STARC bands can provide insight for both ranging and trending markets.
        """

        column_names = {
            "STARC_B": f"STARC_B_{length_sma}_{length_atr}_{multiplier_atr}",
            "STARC_U": f"STARC_U_{length_sma}_{length_atr}_{multiplier_atr}",
        }

        sma = self.data.ta.sma(length=length_sma)
        atr = self.data.ta.atr(length=length_atr)

        self.data[column_names["STARC_B"]] = sma - multiplier_atr * atr
        self.data[column_names["STARC_U"]] = sma + multiplier_atr * atr

        self.indicators["STARC"] = Indicator(
            signal=Signal(
                BUY=lambda x: x["High"] > x[column_names["STARC_U"]],
                SELL=lambda x: x["Low"] < x[column_names["STARC_B"]],
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.MAIN,
                list=[Plot(columns=list(column_names.values()), ylabel="Volatility [STARC]")],
            ),
        )

    def add_mass_index(self, fast: int, slow: int) -> None:
        """
        MASSI (Mass Index)
        https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/mass-index#introduction

        defaults: fast = 9, slow = 25

        The Mass Index is a volatility indicator that does not have a directional bias.
        """

        column_name = f"MASSI_{fast}_{slow}"

        self.data.ta.massi(fast=fast, slow=slow, append=True)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Volatility -> MASSI' can not be added.")
            return

        self.indicators["MASSI"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_name] <= 26,
                SELL=lambda x: x[column_name] <= 26,
            ),
            columns=[column_name],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_name], color="orange", ylabel="Volatility [MASSI]")],
                horizontal_lines=[
                    HorizontalLine(y=27, color="red"),
                    HorizontalLine(y=26, color="black"),
                    HorizontalLine(y=24, color="blue"),
                ],
            ),
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

        column_names = {"BBM": f"BBM_{length}_{std}", "BBL": f"BBL_{length}_{std}", "BBU": f"BBU_{length}_{std}"}

        self.data.ta.bbands(length=length, std=std, append=True)
        if column_names["BBM"] not in self.data.columns:
            log.debug("Indicator 'Volatility -> BBANDS' can not be added.")
            return

        column_name_BBM_lag = column_names["BBM"] + "_lag"
        self.data[column_name_BBM_lag] = self.data[column_names["BBM"]].shift(1)

        self.indicators["BBANDS"] = Indicator(
            signal=Signal(
                BUY=lambda x: (x["Close"] > x[column_names["BBU"]]) and (x[column_names["BBM"]] > x[column_name_BBM_lag]),
                SELL=lambda x: (x["Close"] < x[column_names["BBL"]])
                and (x[column_names["BBM"]] < x[column_name_BBM_lag]),
            ),
            columns=list(column_names.values()) + [column_name_BBM_lag],
            plots=Plots(
                panel=Panel.MAIN,
                list=[Plot(columns=list(column_names.values()), ylabel="Volatility [BBANDS]")],
            ),
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

        column_names = {
            "ACCBU": f"ACCBU_{length}",
            "ACCBM": f"ACCBM_{length}",
            "ACCBL": f"ACCBL_{length}",
        }

        self.data.ta.accbands(length=length, c=c, mamode=mamode, append=True)
        if column_names["ACCBM"] not in self.data.columns:
            log.debug("Indicator 'Volatility -> ACCBANDS' can not be added.")
            return

        self.indicators["ACCBANDS"] = Indicator(
            signal=Signal(
                BUY=lambda x: x["Close"] > x[column_names["ACCBU"]],
                SELL=lambda x: x["Close"] < x[column_names["ACCBL"]],
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.MAIN,
                list=[Plot(columns=list(column_names.values()), ylabel="Volatility [ACCBANDS]")],
            ),
        )


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
