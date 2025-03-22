import pandas_ta as ta  # type: ignore

from services.ta.indicators.models.category_base import IndicatorsCategoryBase
from services.ta.indicators.models.indicator import HorizontalLine, Indicator, Panel, Plot, Plots, Signal
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

        column_names = {
            "PVT": "PVT",
            "PVT_SMA": f"PVT_SMA_{length_sma}",
        }

        self.data.ta.pvt(drift=drift, append=True)
        self.data[column_names["PVT_SMA"]] = self.data.ta.sma(close="PVT", length=length_sma)
        if column_names["PVT"] not in self.data.columns:
            log.debug("Indicator 'Volume -> PVT' can not be added.")
            return

        column_names_slope = {
            "PVT": "PVT_slope",
            "close": f"Close_slope_{length_divergence}",
        }
        self.data[column_names_slope["close"]] = self.data.ta.linreg(length=length_divergence, slope=True)
        self.data[column_names_slope["PVT"]] = self.data.ta.linreg(
            close=column_names["PVT"],
            length=length_divergence,
            slope=True,
        )

        self.indicators["PVT"] = Indicator(
            signal=Signal(
                LONG=lambda x: x[column_names["PVT_SMA"]] < x["PVT"]
                or all(
                    [
                        x[column_names_slope["PVT"]] < 0,
                        x[column_names_slope["close"]] > 0,
                    ],
                ),
                SHORT=lambda x: x[column_names["PVT_SMA"]] > x["PVT"]
                or all(
                    [
                        x[column_names_slope["PVT"]] > 0,
                        x[column_names_slope["close"]] < 0,
                    ],
                ),
            ),
            columns=list(column_names.values()) + list(column_names_slope.values()),
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=list(column_names.values()), ylabel="Volume [PVT]")],
            ),
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

        column_name = f"ADOSC_{fast}_{slow}"

        self.data[column_name] = self.data.ta.adosc(fast=fast, slow=slow)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Volume -> ADOSC' can not be added.")
            return

        column_names_slope = {
            "ADOSC": "ADOSC_slope",
            "close": f"Close_slope_{length_divergence}",
        }
        self.data[column_names_slope["close"]] = self.data.ta.linreg(length=length_divergence, slope=True)
        self.data[column_names_slope["ADOSC"]] = self.data.ta.linreg(
            close=column_name,
            length=length_divergence,
            slope=True,
        )

        column_name_lag = f"{column_name}_lag"
        self.data[column_name_lag] = self.data[column_name].shift(1)

        self.indicators["ADOSC"] = Indicator(
            signal=Signal(
                LONG=lambda x: x[column_name] > x[column_name_lag]
                or all(
                    [
                        x[column_names_slope["ADOSC"]] > 0,
                        x[column_names_slope["close"]] < 0,
                    ],
                ),
                SHORT=lambda x: x[column_name] < x[column_name_lag]
                or all(
                    [
                        x[column_names_slope["ADOSC"]] < 0,
                        x[column_names_slope["close"]] > 0,
                    ],
                ),
            ),
            columns=[column_name, column_name_lag] + list(column_names_slope.values()),
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_name], ylabel="Volume [ADOSC]")],
            ),
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

        column_name = f"CMF_{length}"

        self.data.ta.cmf(length=length, append=True)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Volume -> CMF' can not be added.")
            return

        column_names_slope = {
            "CMF": "CMF_slope",
            "close": f"Close_slope_{length_divergence}",
        }
        self.data[column_names_slope["close"]] = self.data.ta.linreg(length=length_divergence, slope=True)
        self.data[column_names_slope["CMF"]] = self.data.ta.linreg(
            close=column_name,
            length=length_divergence,
            slope=True,
        )

        self.indicators["CMF"] = Indicator(
            signal=Signal(
                LONG=lambda x: x[column_name] > 0.1
                or all(
                    [
                        x[column_names_slope["CMF"]] > 0,
                        x[column_names_slope["close"]] < 0,
                    ],
                ),
                SHORT=lambda x: x[column_name] < -0.1
                or all(
                    [
                        x[column_names_slope["CMF"]] < 0,
                        x[column_names_slope["close"]] > 0,
                    ],
                ),
            ),
            columns=[column_name] + list(column_names_slope.values()),
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_name], color="orange", ylabel="Volume [CMF]")],
                horizontal_lines=[HorizontalLine(y=0, color="black")],
            ),
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

        column_names = {
            "KVO": f"KVO_{fast}_{slow}_{signal}",
            "KVOs": f"KVOs_{fast}_{slow}_{signal}",
        }

        self.data.ta.kvo(fast=fast, slow=slow, signal=signal, mamode=mamode, append=True)
        if column_names["KVO"] not in self.data.columns:
            log.debug("Indicator 'Volume -> KVO' can not be added.")
            return

        column_names_slope = {
            "KVO": "KVO_slope",
            "close": f"Close_slope_{length_divergence}",
        }
        self.data[column_names_slope["close"]] = self.data.ta.linreg(length=length_divergence, slope=True)
        self.data[column_names_slope["KVO"]] = self.data.ta.linreg(
            close=column_names["KVO"],
            length=length_divergence,
            slope=True,
        )

        self.indicators["KVO"] = Indicator(
            signal=Signal(
                LONG=lambda x: all(
                    [
                        x[column_names["KVO"]] > x[column_names["KVOs"]],
                        x[column_names["KVOs"]] > 0,
                    ],
                )
                or all(
                    [
                        x[column_names_slope["KVO"]] > 0,
                        x[column_names_slope["close"]] < 0,
                    ],
                ),
                SHORT=lambda x: all(
                    [
                        x[column_names["KVO"]] < x[column_names["KVOs"]],
                        x[column_names["KVOs"]] < 0,
                    ],
                )
                or all(
                    [
                        x[column_names_slope["KVO"]] < 0,
                        x[column_names_slope["close"]] > 0,
                    ],
                ),
            ),
            columns=list(column_names.values()) + list(column_names_slope.values()),
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=list(column_names.values()), ylabel="Volume [KVO]")],
            ),
        )
