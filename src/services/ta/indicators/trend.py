import pandas_ta as ta  # type: ignore

from services.ta.indicators.models.category_base import IndicatorsCategoryBase
from services.ta.indicators.models.indicator import HorizontalLine, Indicator, Panel, Plot, Plots, Signal
from utils.logger.operators import get_logger

log = get_logger()


class Trend(IndicatorsCategoryBase):
    def add_trend_intensity_index(self, length_sma: int, length_signal: int) -> None:
        """
        TII (Trend Intensity Index)
        https://raposa.trade/blog/4-ways-to-trade-the-trend-intensity-indicator/

        Determining the strength of a trend can provide a valuable edge to your trading strategy
        and help you determine when to go long and let it ride, or not. This is what the Trend
        Intensity Indicator (TII) was designed to do.

        This indicator is as simple to interpret as more familiar values like the RSI. It's scaled
        from 0-100 where higher numbers indicate a stronger upward trend, lower values a stronger
        downward trend, and values around the centerline (50) are neutral.
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

        self.indicators["TII"] = Indicator(
            signal=Signal(
                LONG=lambda x: (x[column_names["TII"]] - x[column_names["TII_SIGNAL"]] > 2)
                and (x[column_names["TII_SIGNAL"]] > 50),
                SHORT=lambda x: (x[column_names["TII_SIGNAL"]] - x[column_names["TII"]] > 2)
                and (x[column_names["TII_SIGNAL"]] < 50),
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=list(column_names.values()), ylabel="Trend [TII]")],
                horizontal_lines=[HorizontalLine(y=50, color="red")],
            ),
        )

    def add_average_directional_movement(self, length: int, lensig: int, mamode: str) -> None:
        """
        ADX (Average Directional Movement)
        https://www.investopedia.com/terms/w/wilders-dmi-adx.asp

        defaults: length = 14, lensig = length, mamode = "rma"

        Wilder's DMI (ADX) consists of three indicators that measure a trend's strength and
        direction. Three lines compose the Direction Movement Index (DMI): ADX (black line),
        DI+ (green line), and DI- (red line). The Average Directional Index (ADX) line shows
        the strength of the trend. The higher the ADX value, the stronger the trend. The color
        of the lines can be altered, but black, green, and red are the default in most software.

        The Plus Direction Indicator (DI+) and Minus Direction Indicator (DI-) show the current
        price direction. When the DI+ is above DI-, the current price momentum is up. When the
        DI- is above DI+, the current price momentum is down.
        """

        column_names = {
            "ADX": f"ADX_{lensig}",
            "DMN": f"DMN_{length}",
            "DMP": f"DMP_{length}",
        }

        self.data.ta.adx(length=length, lensig=lensig, mamode=mamode, append=True)
        if column_names["ADX"] not in self.data.columns:
            log.debug("Indicator 'Trend -> ADX' can not be added.")
            return

        self.indicators["ADX"] = Indicator(
            signal=Signal(
                LONG=lambda x: x[column_names["ADX"]] > 22 and x[column_names["DMP"]] > x[column_names["DMN"]],
                SHORT=lambda x: x[column_names["ADX"]] > 22 and x[column_names["DMP"]] < x[column_names["DMN"]],
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=list(column_names.values()), ylabel="Trend [ADX]")],
                horizontal_lines=[HorizontalLine(y=22, color="black")],
            ),
        )

    def add_parabolic_stop_and_reverse(self, acceleration: float, maximum: float) -> None:
        """
        PSAR (Parabolic Stop and Reverse)
        https://www.investopedia.com/terms/p/parabolicindicator.asp

        defaults: af0=0.02, af=0.02, max_af=0.2

        For best results, traders should use the parabolic indicator with other technical indicators that
        indicate whether a market is trending or not, such as the average directional index (ADX), a moving
        average (MA), or a trendline.
        For example, traders might confirm a PSAR buy signal with an ADX reading above 30 and a bounce for a
        long-term rising trendline.
        """

        column_names = {
            "PSARl": f"PSARl_{acceleration}_{maximum}",  # lower branch
            "PSARs": f"PSARs_{acceleration}_{maximum}",  # upper branch
        }

        self.data.ta.psar(af=acceleration, max_af=maximum, append=True)
        if column_names["PSARl"] not in self.data.columns:
            log.debug("Indicator 'Trend -> PSAR' can not be added.")
            return

        self.indicators["PSAR"] = Indicator(
            signal=Signal(
                LONG=lambda x: x["Close"] > x[column_names["PSARl"]],
                SHORT=lambda x: x["Close"] < x[column_names["PSARs"]],
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.MAIN,
                list=[Plot(columns=list(column_names.values()), ylabel="Trend [PSAR]", type="scatter")],
            ),
        )

    def add_choppiness_index(self, length: int, length_atr: int, scalar: float) -> None:
        """
        CHOP (Choppiness Index)
        https://www.tradingview.com/support/solutions/43000501980-choppiness-index-chop/

        defaults: length=14, scalar=100, length_atr=1

        Values closer to 100 implies the underlying is choppier
        whereas values closer to 0 implies the underlying is trending.
        """

        column_name = f"CHOP_{length}_{length_atr}_{scalar}"

        self.data.ta.chop(length=length, atr_length=length_atr, scalar=scalar, append=True)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Trend -> CHOP' can not be added.")
            return

        self.indicators["CHOP"] = Indicator(
            signal=Signal(
                EXIT=lambda x: x[column_name] > 55,
            ),
            columns=[column_name],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_name], color="orange", ylim=[0, 100], ylabel="Trend [CHOP]")],
                horizontal_lines=[HorizontalLine(y=50, color="red")],
            ),
        )
