import pandas_ta as ta  # type: ignore

from services.ta.indicators.models import HorizontalLine, Indicator, Panel, Plot, Plots, Signal
from services.ta.indicators.models.category_base import IndicatorsCategoryBase
from utils.logger import get_logger

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
                BUY=lambda x: (x[column_names["TII"]] - x[column_names["TII_SIGNAL"]] > 2)
                and (x[column_names["TII_SIGNAL"]] > 50),
                SELL=lambda x: (x[column_names["TII_SIGNAL"]] - x[column_names["TII"]] > 2)
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

        Wilder’s DMI (ADX) consists of three indicators that measure a trend’s strength and
        direction. Three lines compose the Direction Movement Index (DMI): ADX (black line),
        DI+ (green line), and DI- (red line). The Average Directional Index (ADX) line shows
        the strength of the trend. The higher the ADX value, the stronger the trend. The color
        of the lines can be altered, but black, green, and red are the default in most software.

        The Plus Direction Indicator (DI+) and Minus Direction Indicator (DI-) show the current
        price direction. When the DI+ is above DI-, the current price momentum is up. When the
        DI- is above DI+, the current price momentum is down.
        """

        column_names = {"ADX": f"ADX_{lensig}", "DMP": f"DMP_{length}", "DMN": f"DMN_{length}"}

        self.data.ta.adx(length=length, lensig=lensig, mamode=mamode, append=True)
        if column_names["ADX"] not in self.data.columns:
            log.debug("Indicator 'Trend -> ADX' can not be added.")
            return

        self.indicators["ADX"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_names["ADX"]] > 25 and x[column_names["DMP"]] > x[column_names["DMN"]],
                SELL=lambda x: x[column_names["ADX"]] > 25 and x[column_names["DMP"]] < x[column_names["DMN"]],
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=list(column_names.values()), ylabel="Trend [ADX]")],
                horizontal_lines=[HorizontalLine(y=25, color="orange")],
            ),
        )

    def add_vertical_horizontal_filter(self, length: int, length_ema: int) -> None:
        """
        >>> not used

        VHF (Vertical Horizontal Filter)
        https://www.incrediblecharts.com/indicators/vertical_horizontal_filter.php
        https://trendspider.com/learning-center/introduction-to-vertical-horizontal-filter/

        defaults: length = 28

        Vertical Horizontal Filter (VHF) was created by Adam White to identify trending and
        ranging markets. VHF measures the level of trend activity, similar to ADX in the
        Directional Movement System. Trend indicators can then be employed in trending markets
        and momentum indicators in ranging markets.

        Vary the number of periods in the Vertical Horizontal Filter to suit different time frames.
        White originally recommended 28 days but now prefers an 18-day window smoothed with
        a 6-day moving average.
        """

        column_name = f"VHF_{length}_EMA_{length_ema}"

        self.data[column_name] = self.data.ta.ema(
            close=self.data.ta.vhf(length=length),
            length=length_ema,
        )
        if column_name not in self.data.columns:
            log.debug("Indicator 'Trend -> VHF' can not be added.")
            return

        self.indicators["VHF"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_name] > 0.45,
                SELL=lambda x: x[column_name] > 0.4,
            ),
            columns=[column_name],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_name], color="orange", ylabel="Trend [VHF]")],
                horizontal_lines=[HorizontalLine(y=0.45, color="red"), HorizontalLine(y=0.4, color="blue")],
            ),
        )

    def add_vortex_indicator(self, length: int, drift: int) -> None:
        """
        >>> not used

        VORTEX (Vortex Indicator)
        https://www.investopedia.com/terms/v/vortex-indicator-vi.asp

        defaults: length=14, drift=1

        The vortex indicator is commonly used in conjunction with
        other reversal trend patterns to help support a reversal signal.
        An uptrend or buy signal occurs when VI+ is below VI- and then
        crosses above VI- to take the top position among the trendlines.
        A downtrend or sell signal occurs when VI- is below VI+ and
        crosses above VI+ to take the top position among the trendlines.
        """

        column_names = {
            "VTXP": f"VTXP_{length}",
            "VTXM": f"VTXM_{length}",
        }

        self.data.ta.vortex(length=length, drift=drift, append=True)
        if column_names["VTXP"] not in self.data.columns:
            log.debug("Indicator 'Trend -> VORTEX' can not be added.")
            return

        self.indicators["VORTEX"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_names["VTXP"]] > x[column_names["VTXM"]],
                SELL=lambda x: x[column_names["VTXM"]] < x[column_names["VTXP"]],
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_names["VTXP"], column_names["VTXM"]], ylabel="Trend [VORTEX]")],
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
                BUY=lambda x: x["Close"] > x[column_names["PSARl"]],
                SELL=lambda x: x["Close"] < x[column_names["PSARs"]],
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
                BUY=lambda x: x[column_name] < 50,
                SELL=lambda x: x[column_name] < 50,
            ),
            columns=[column_name],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_name], color="orange", ylim=[0, 100], ylabel="Trend [CHOP]")],
                horizontal_lines=[HorizontalLine(y=50, color="red")],
            ),
        )

    def add_chande_kroll_stop(self, p: int, x: float, q: int) -> None:
        """
        CKSP (Chande Kroll Stop)
        https://www.tradingview.com/support/solutions/43000589105-chande-kroll-stop/

        p (int): ATR and first stop period.
        x (float): ATR scalar.
        q (int): Second stop period.

        defaults: TradingView(p=10, x=1, q=9), Book(p=10, x=3, q=20)

        It is a trend-following indicator, identifying your stop by calculating the average
        true range of the recent market volatility.
        """

        column_names = {
            "CKSPl": f"CKSPl_{p}_{x}_{q}",  # stop for long positions
            "CKSPs": f"CKSPs_{p}_{x}_{q}",  # stop for short positions
        }

        self.data.ta.cksp(p=p, x=x, q=q, append=True)
        if column_names["CKSPl"] not in self.data.columns:
            log.debug("Indicator 'Trend -> CKSP' can not be added.")
            return

        self.indicators["CKSP"] = Indicator(
            signal=Signal(
                BUY=lambda x: x["Close"] > x[column_names["CKSPl"]],
                SELL=lambda x: x["Close"] < x[column_names["CKSPs"]],
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.MAIN,
                list=[Plot(columns=[column_names["CKSPl"], column_names["CKSPs"]], ylabel="Trend [CKSP]")],
            ),
        )
