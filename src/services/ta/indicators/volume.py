import pandas_ta as ta  # type: ignore

from services.ta.indicators.models import HorizontalLine, Indicator, Panel, Plot, Plots, Signal
from services.ta.indicators.models.category_base import IndicatorsCategoryBase
from utils.logger import get_logger

log = get_logger()


class Volume(IndicatorsCategoryBase):
    def add_price_volume_trend(self, drift: int, length_sma: int) -> None:
        """
        PVT (Price Volume Trend)
        https://www.strike.money/technical-analysis/volume-price-trend

        default: drift=1

        Price Volume Trend (PVT) is a technical analysis indicator that relates price and volume.
        A sharply rising VPT when the price is breaking out from a price range indicates strong
        buying pressure. This indicates that market participants are interested in buying as the
        volume is rising during a period of price rise. Conversely, a sharply declining VPT when
        the price is breaking down from a price range indicates strong selling pressure.
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

        self.indicators["PVT"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_names["PVT_SMA"]] < x["PVT"],
                SELL=lambda x: x[column_names["PVT_SMA"]] > x["PVT"],
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=list(column_names.values()), ylabel="Volume [PVT]")],
            ),
        )

    def add_accumulation_distribution_oscillator(self, fast: int, slow: int) -> None:
        """
        ADOSC (Accumulation/Distribution Oscillator)
        https://www.investopedia.com/articles/active-trading/031914/understanding-chaikin-oscillator.asp
        https://www.investopedia.com/terms/a/accumulationdistribution.asp

        default: fast=12, slow=26

        Accumulation/Distribution Oscillator indicator utilizes Accumulation/Distribution and treats it
        similarly to MACD or APO.
        """

        column_name = f"ADOSC_{fast}_{slow}"

        self.data[column_name] = self.data.ta.adosc(fast=fast, slow=slow)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Volume -> ADOSC' can not be added.")
            return

        column_name_lag = f"{column_name}_lag"
        self.data[column_name_lag] = self.data[column_name].shift(1)

        self.indicators["ADOSC"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_name] > x[column_name_lag],
                SELL=lambda x: x[column_name] < x[column_name_lag],
            ),
            columns=[column_name, column_name_lag],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_name], ylabel="Volume [ADOSC]")],
            ),
        )

    def add_chaikin_money_flow(self, length: int) -> None:
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

        self.indicators["CMF"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_name] > 0.1,
                SELL=lambda x: x[column_name] < -0.1,
                EXIT=lambda x: x[column_name] == 0,
            ),
            columns=[column_name],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_name], color="orange", ylabel="Volume [CMF]")],
                horizontal_lines=[HorizontalLine(y=0, color="black")],
            ),
        )

    def add_klinger_volume_oscillator(self, fast: int, slow: int, signal: int, mamode: str) -> None:
        """
        KVO (Klinger Volume Oscillator)
        https://www.investopedia.com/terms/k/klingeroscillator.asp

        default: fast=34, slow=55, signal=13, mamode="ema"


        This indicator was developed by Stephen J. Klinger. It is designed to predict
        price reversals in a market by comparing volume to price.
        """

        column_names = {
            "KVO": f"KVO_{fast}_{slow}_{signal}",
            "KVOs": f"KVOs_{fast}_{slow}_{signal}",
        }

        self.data.ta.kvo(fast=fast, slow=slow, signal=signal, mamode=mamode, append=True)
        if column_names["KVO"] not in self.data.columns:
            log.debug("Indicator 'Volume -> KVO' can not be added.")
            return

        self.indicators["KVO"] = Indicator(
            signal=Signal(
                BUY=lambda x: (x[column_names["KVO"]] > x[column_names["KVOs"]]) and (x[column_names["KVOs"]] > 0),
                SELL=lambda x: (x[column_names["KVO"]] < x[column_names["KVOs"]]) and (x[column_names["KVOs"]] < 0),
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=list(column_names.values()), ylabel="Volume [KVO]")],
            ),
        )


#     # Volume
#     @staticmethod
#     def volume_flow(
#         data: pd.DataFrame,
#         period: int,
#         smooth: int,
#         ma_period: int,
#         coef: float,
#         vol_coef: float,
#     ) -> pd.DataFrame:
#         """https://precisiontradingsystems.com/volume-flow.htm"""

#         make_name = lambda x: f"{x}_{period}_{smooth}_{ma_period}_{coef}_{vol_coef}"

#         data["_inter"] = np.log(data["Close"]).diff()  # type: ignore
#         data["_vinter"] = ta.stdev(data["_inter"], length=30)
#         data["_cutoff"] = coef * data["_vinter"] * data["Close"]
#         data["_vave"] = ta.sma(data["Volume"], length=period).shift(1)  # type: ignore
#         data["_vmax"] = data["_vave"] * vol_coef
#         data["_mf"] = data["Close"] - data["Close"].shift(1)
#         data["_vcp"] = np.where(
#             data["_mf"] > data["_cutoff"],
#             data["Volume"].clip(upper=data["_vmax"]),
#             np.where(
#                 data["_mf"] < -data["_cutoff"],
#                 -data["Volume"].clip(upper=data["_vmax"]),
#                 0,
#             ),
#         )
#         data[make_name("VFI")] = ta.ema(
#             ta.sma(data["_vcp"], length=period) / data["_vave"], length=smooth  # type: ignore
#         )
#         data[make_name("VFI_MA")] = ta.sma(
#             ta.ema(
#                 ta.sma(data["_vcp"], length=period) / data["_vave"], length=smooth  # type: ignore
#             ),
#             length=ma_period,
#         )

#         return data
