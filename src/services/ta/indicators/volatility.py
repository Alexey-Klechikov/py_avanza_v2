import pandas_ta as ta  # pylint: disable=unused-import # noqa: F401 # noqa: F401
from pandas_ta.overlap import wma

from services.ta.indicators.models.category_base import IndicatorsCategoryBase
from services.ta.indicators.models.indicator import HorizontalLine, Indicator, Panel, Plot, Plots, Signal
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

        column_names = {
            "STARC_B": f"STARC_B_{length_ma}_{length_atr}_{multiplier_atr}",
            "STARC_U": f"STARC_U_{length_ma}_{length_atr}_{multiplier_atr}",
        }

        ma = wma(self.data["Close"], length=length_ma)
        atr = self.data.ta.atr(length=length_atr)

        self.data[column_names["STARC_B"]] = ma - multiplier_atr * atr
        self.data[column_names["STARC_U"]] = ma + multiplier_atr * atr

        self.indicators["STARC"] = Indicator(
            signal=Signal(
                LONG=lambda x: x["High"] > x[column_names["STARC_U"]],
                SHORT=lambda x: x["Low"] < x[column_names["STARC_B"]],
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.MAIN,
                list=[Plot(columns=list(column_names.values()), ylabel="Volatility [STARC]")],
            ),
        )

    def add_mass_index(self, fast: int, slow: int, threshold: int) -> None:
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
            signal=Signal(LONG=lambda x: x[column_name] <= threshold, SHORT=lambda x: x[column_name] <= threshold),
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
        column_names = {
            "BBM": f"BBM_{length}_{std}_{std}",
            "BBL": f"BBL_{length}_{std}_{std}",
            "BBU": f"BBU_{length}_{std}_{std}",
        }

        self.data.ta.bbands(length=length, lower_std=std, upper_std=std, append=True)

        if column_names["BBM"] not in self.data.columns:
            log.debug("Indicator 'Volatility -> BBANDS' can not be added.")
            return

        self.indicators["BBANDS"] = Indicator(
            signal=Signal(
                LONG=lambda x: (x["Close"] > x[column_names["BBU"]]),
                SHORT=lambda x: (x["Close"] < x[column_names["BBL"]]),
            ),
            columns=list(column_names.values()),
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

        column_names = {"ACCBU": f"ACCBU_{length}", "ACCBM": f"ACCBM_{length}", "ACCBL": f"ACCBL_{length}"}

        self.data.ta.accbands(length=length, c=c, mamode=mamode, append=True)
        if column_names["ACCBM"] not in self.data.columns:
            log.debug("Indicator 'Volatility -> ACCBANDS' can not be added.")
            return

        self.indicators["ACCBANDS"] = Indicator(
            signal=Signal(
                LONG=lambda x: x["Close"] > x[column_names["ACCBU"]],
                SHORT=lambda x: x["Close"] < x[column_names["ACCBL"]],
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.MAIN,
                list=[Plot(columns=list(column_names.values()), ylabel="Volatility [ACCBANDS]")],
            ),
        )
