from contextlib import suppress

import pandas_ta as ta  # pylint: disable=unused-import # noqa: F401

from services.ta.indicators.models.category_base import IndicatorsCategoryBase
from services.ta.indicators.models.indicator import Indicator, IndicatorSignal
from utils.logger.operators import get_logger

log = get_logger()


class Volume(IndicatorsCategoryBase):
    def add_price_volume_trend(self, drift: int, length_sma: int, length_divergence: int) -> None:
        """
        PVT (Price Volume Trend)
        https://www.strike.money/technical-analysis/volume-price-trend

        default: drift=1

        Price Volume Trend (PVT) is a technical analysis indicator that relates price and volume.
        A sharply rising VPT when the price is breaking out from a price range indicates strong
        buying pressure. This indicates that market participants are interested in buying as the
        volume is rising during a period of price rise. Conversely, a sharply declining VPT when
        the price is breaking down from a price range indicates strong selling pressure.

        The Volume Price Trend can help traders identify a potential trend reversal through divergence.
        A divergence occurs when the price and indicators move opposite to each other. For example,
        A VPT divergence occurs when the price of an asset is rising but the VPT line is declining.
        """
        pvt_column, sma_column, slope_column = "PVT", f"PVT_SMA_{length_sma}", "PVT_slope"

        self.bars.ta.pvt(drift=drift, append=True)
        if pvt_column not in self.bars.columns:
            log.debug("Indicator 'Volume -> PVT' can not be added.")
            return

        self.bars[sma_column] = self.bars.ta.sma(close=pvt_column, length=length_sma)
        close_slope_column = self._add_divergence_slopes(pvt_column, slope_column, length_divergence)

        self.indicators["PVT"] = Indicator(
            signal=IndicatorSignal(
                LONG=lambda x: x[sma_column] < x[pvt_column] or (x[slope_column] < 0 and x[close_slope_column] > 0),
                SHORT=lambda x: x[sma_column] > x[pvt_column] or (x[slope_column] > 0 and x[close_slope_column] < 0),
            ),
            columns=[pvt_column, sma_column, slope_column, close_slope_column],
        )

    def add_accumulation_distribution_oscillator(self, fast: int, slow: int, length_divergence: int) -> None:
        """
        ADOSC (Accumulation/Distribution Oscillator)
        https://www.investopedia.com/articles/active-trading/031914/understanding-chaikin-oscillator.asp
        https://www.investopedia.com/terms/a/accumulationdistribution.asp

        default: fast=12, slow=26

        Accumulation/Distribution Oscillator indicator utilizes Accumulation/Distribution and treats it
        similarly to MACD or APO.

        The accumulation/distribution indicator (A/D) is a cumulative indicator that uses volume and price
        to assess whether a stock is being accumulated or distributed. The A/D measure seeks to identify
        divergences between the stock price and the volume flow. This provides insight into how strong a
        trend is. If the price is rising but the indicator is falling, then it suggests that buying or
        accumulation volume may not be enough to support the price rise and a price decline could be
        forthcoming.
        """
        adosc_column, previous_column, slope_column = f"ADOSC_{fast}_{slow}", f"ADOSC_{fast}_{slow}_lag", "ADOSC_slope"

        self.bars[adosc_column] = self.bars.ta.adosc(fast=fast, slow=slow)
        close_slope_column = self._add_divergence_slopes(adosc_column, slope_column, length_divergence)
        self.bars[previous_column] = self.bars[adosc_column].shift(1)

        self.indicators["ADOSC"] = Indicator(
            signal=IndicatorSignal(
                LONG=lambda x: x[adosc_column] > x[previous_column]
                or (x[slope_column] > 0 and x[close_slope_column] < 0),
                SHORT=lambda x: x[adosc_column] < x[previous_column]
                or (x[slope_column] < 0 and x[close_slope_column] > 0),
            ),
            columns=[adosc_column, previous_column, slope_column, close_slope_column],
        )

    def add_chaikin_money_flow(self, length: int, length_divergence: int) -> None:
        """
        CMF (Chaikin Money Flow)
        https://www.chaikinanalytics.com/chaikin-money-flow/

        default: length=21

        Chaikin Money Flow (CMF) is a technical analysis indicator that measures the buying and
        selling pressure of a security over a set period of time. It is based on the concept of
        Money Flow Volume, which is the volume-weighted average of accumulation and distribution
        """
        cmf_column, slope_column = f"CMF_{length}", "CMF_slope"

        self.bars.ta.cmf(length=length, append=True)
        if cmf_column not in self.bars.columns:
            log.debug("Indicator 'Volume -> CMF' can not be added.")
            return

        close_slope_column = self._add_divergence_slopes(cmf_column, slope_column, length_divergence)

        self.indicators["CMF"] = Indicator(
            signal=IndicatorSignal(
                LONG=lambda x: x[cmf_column] > 0.1 or (x[slope_column] > 0 and x[close_slope_column] < 0),
                SHORT=lambda x: x[cmf_column] < -0.1 or (x[slope_column] < 0 and x[close_slope_column] > 0),
            ),
            columns=[cmf_column, slope_column, close_slope_column],
        )

    def add_klinger_volume_oscillator(
        self,
        fast: int,
        slow: int,
        signal: int,
        mamode: str,
        length_divergence: int,
    ) -> None:
        """
        KVO (Klinger Volume Oscillator)
        https://www.investopedia.com/terms/k/klingeroscillator.asp

        default: fast=34, slow=55, signal=13, mamode="ema"

        This indicator was developed by Stephen J. Klinger. It is designed to predict
        price reversals in a market by comparing volume to price.

        The Klinger oscillator also uses divergence to identify when the indicator's inputs are
        not confirming the direction of the price move. It's a bullish sign when the value of the
        indicator is heading upward while the price of the security continues to fall. It is a bearish
        signal when the price is rising but the indicator is falling. Divergence can be coupled with
        signal line crossovers to generate trades. For example, if a bearish divergence forms, a sell
        or short-sell could be initiated the next time the Klinger crosses below the signal line.
        """
        kvo_column = f"KVO_{fast}_{slow}_{signal}"
        signal_column = f"KVOs_{fast}_{slow}_{signal}"
        slope_column = "KVO_slope"

        # pandas_ta's kvo has raised AttributeError on some histories (51f7b8e): treat that as not computable
        with suppress(AttributeError):
            self.bars.ta.kvo(fast=fast, slow=slow, signal=signal, mamode=mamode, append=True)

        if kvo_column not in self.bars.columns:
            log.debug("Indicator 'Volume -> KVO' can not be added.")
            return

        close_slope_column = self._add_divergence_slopes(kvo_column, slope_column, length_divergence)

        self.indicators["KVO"] = Indicator(
            signal=IndicatorSignal(
                LONG=lambda x: (x[kvo_column] > x[signal_column] and x[signal_column] > 0)
                or (x[slope_column] > 0 and x[close_slope_column] < 0),
                SHORT=lambda x: (x[kvo_column] < x[signal_column] and x[signal_column] < 0)
                or (x[slope_column] < 0 and x[close_slope_column] > 0),
            ),
            columns=[kvo_column, signal_column, slope_column, close_slope_column],
        )
