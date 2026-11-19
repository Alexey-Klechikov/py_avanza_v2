import pandas_ta as ta  # pylint: disable=unused-import # noqa: F401

from services.ta.indicators.models.category_base import IndicatorsCategoryBase
from services.ta.indicators.models.indicator import Indicator, IndicatorSignal
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
        tii_column = f"TII_{length_sma}_{length_signal}"
        signal_column = f"TII_SIGNAL_{length_sma}_{length_signal}"

        is_above_sma = self.bars["Close"] > self.bars.ta.sma(length=length_sma)
        bars_above_sma = is_above_sma.astype(int).rolling(length_sma // 2).sum()
        self.bars[tii_column] = 200 * bars_above_sma / length_sma
        self.bars[signal_column] = self.bars.ta.ema(close=self.bars[tii_column], length=length_signal)

        self.indicators["TII"] = Indicator(
            signal=IndicatorSignal(
                LONG=lambda x: x[tii_column] - x[signal_column] > 2 and x[signal_column] > 50,
                SHORT=lambda x: x[signal_column] - x[tii_column] > 2 and x[signal_column] < 50,
            ),
            columns=[tii_column, signal_column],
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
        adx_column, minus_di_column, plus_di_column = f"ADX_{lensig}", f"DMN_{length}", f"DMP_{length}"
        self.bars.ta.adx(length=length, signal_length=lensig, mamode=mamode, append=True)
        if adx_column not in self.bars.columns:
            log.debug("Indicator 'Trend -> ADX' can not be added.")
            return

        self.indicators["ADX"] = Indicator(
            signal=IndicatorSignal(
                LONG=lambda x: x[adx_column] > 22 and x[plus_di_column] > x[minus_di_column],
                SHORT=lambda x: x[adx_column] > 22 and x[plus_di_column] < x[minus_di_column],
            ),
            columns=[adx_column, minus_di_column, plus_di_column],
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
        lower_column = f"PSARl_{acceleration}_{maximum}"
        upper_column = f"PSARs_{acceleration}_{maximum}"

        self.bars.ta.psar(af=acceleration, max_af=maximum, append=True)
        if lower_column not in self.bars.columns:
            log.debug("Indicator 'Trend -> PSAR' can not be added.")
            return

        self.indicators["PSAR"] = Indicator(
            signal=IndicatorSignal(
                LONG=lambda x: x["Close"] > x[lower_column],
                SHORT=lambda x: x["Close"] < x[upper_column],
            ),
            columns=[lower_column, upper_column],
        )
