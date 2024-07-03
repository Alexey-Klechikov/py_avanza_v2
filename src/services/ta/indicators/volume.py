import pandas_ta as ta  # type: ignore

from services.ta.indicators.models import HorizontalLine, Indicator, Panel, Plot, Plots, Signal
from services.ta.indicators.models.category_base import IndicatorsCategoryBase
from utils.logger import get_logger

log = get_logger()


class Volume(IndicatorsCategoryBase):
    def add_price_volume_trend(self, length_sma: int) -> None:
        # TODO: double-check this indicator
        """
        PVT (Price Volume Trend)
        """

        column_names = {
            "PVT": "PVT",
            "PVT_SMA": f"PVT_SMA_{length_sma}",
        }

        self.data.ta.pvt(append=True)
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
                list=[Plot(columns=[column_names["PVT"], column_names["PVT_SMA"]], ylabel="Volume [PVT]")],
            ),
        )

    def add_accumulation_distribution_oscillator(self, fast: int, slow: int) -> None:
        # TODO: double-check this indicator
        # TODO: Add plotting
        """
        ADOSC (Accumulation/Distribution Oscillator)
        """
        column_name = "ADOSC_direction"

        self.data[column_name] = (
            self.data.ta.adosc(fast=fast, slow=slow).rolling(2).apply(lambda x: x.iloc[1] > x.iloc[0])
        )
        if column_name not in self.data.columns:
            log.debug("Indicator 'Volume -> ADOSC' can not be added.")
            return

        self.indicators["ADOSC"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_name] == 1,
                SELL=lambda x: x[column_name] == 0,
            ),
            columns=[column_name],
        )

    def add_chaikin_money_flow(self, length: int) -> None:
        """
        CMF (Chaikin Money Flow)
        """

        column_name = f"CMF_{length}"

        self.data.ta.cmf(length=length, append=True)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Volume -> CMF' can not be added.")
            return

        cmf = {"max": self.data[column_name].max(), "min": self.data[column_name].min()}
        self.indicators["CMF"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_name] > cmf["max"] * 0.2,
                SELL=lambda x: x[column_name] < cmf["min"] * 0.2,
            ),
            columns=[column_name],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_name], color="orange", ylabel="Volume [CMF]")],
                horizontal_lines=[HorizontalLine(y=0, color="black")],
            ),
        )

    def add_elders_force_index(self, length: int, mamode: str) -> None:
        # TODO: add plot
        """
        EFI (Elder's Force Index)
        """

        column_name = f"EFI_{length}"

        self.data.ta.efi(length=length, mamode=mamode, append=True)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Volume -> EFI' can not be added.")
            return

        self.indicators["EFI"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_name] > 0,
                SELL=lambda x: x[column_name] < 0,
            ),
            columns=[column_name],
        )

    def add_klinger_volume_oscillator(self, fast: int, slow: int, signal: int) -> None:
        """
        KVO (Klinger Volume Oscillator)
        """

        column_names = {
            "KVO": f"KVO_{fast}_{slow}_{signal}",
            "KVOs": f"KVOs_{fast}_{slow}_{signal}",
        }

        self.data.ta.kvo(fast=fast, slow=slow, signal=signal, mamode="ema", append=True)
        if column_names["KVO"] not in self.data.columns:
            log.debug("Indicator 'Volume -> KVO' can not be added.")
            return

        self.indicators["KVO"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_names["KVO"]] > x[column_names["KVOs"]],
                SELL=lambda x: x[column_names["KVO"]] < x[column_names["KVOs"]],
            ),
            columns=list(column_names.values()),
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_names["KVO"], column_names["KVOs"]], ylabel="Volume [KVO]")],
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
