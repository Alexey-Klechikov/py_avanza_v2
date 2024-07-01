import warnings

import pandas as pd
from avanza import OrderType

from data.settings import DATA_COLUMNS
from utils.logger import get_logger

warnings.filterwarnings("ignore")
pd.options.mode.chained_assignment = None
pd.set_option("display.expand_frame_repr", False)

log = get_logger()


class Indicators:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.conditions = dict()
        self.columns_needed = set()

    def remove_extra_columns(self):
        self.data = self.data[DATA_COLUMNS + list(self.columns_needed)]


class CategoryBase:
    def __init__(self, indicators: Indicators) -> None:
        self.indicators = indicators
        self._conditions = {}
        self._columns_needed = []

    def add_all(self) -> None:
        self.indicators.conditions[self.__class__.__name__] = self._conditions
        self.indicators.columns_needed |= set(self._columns_needed)
        self.indicators.remove_extra_columns()


class Trend(CategoryBase):
    def _add_trend_intensity_index(self, length_sma: int, length_signal: int) -> None:
        # TODO: double-check this indicator
        """
        TII (Trend Intensity Index)
        https://raposa.trade/blog/4-ways-to-trade-the-trend-intensity-indicator/
        """

        column_names = {
            "TII": f"TII_{length_sma}_{length_signal}",
            "TII_SIGNAL": f"TII_SIGNAL_{length_sma}_{length_signal}",
        }

        sma = self.indicators.data.ta.sma(length=length_sma)
        diff = self.indicators.data["Close"] - sma
        pos_count = diff.map(lambda x: 1 if x > 0 else 0).rolling(int(length_sma / 2)).sum()
        self.indicators.data[column_names["TII"]] = 200 * (pos_count) / length_sma
        self.indicators.data[column_names["TII_SIGNAL"]] = self.indicators.data.ta.ema(
            close=self.indicators.data[column_names["TII"]],
            length=length_signal,
        )

        self._conditions["TII"] = {
            OrderType.BUY: lambda x: x[column_names["TII_SIGNAL"]] > x[column_names["TII"]],
            OrderType.SELL: lambda x: x[column_names["TII_SIGNAL"]] < x[column_names["TII"]],
        }

        self._columns_needed += column_names.values()

    def _add_trend_based_on_ttm_squeeze(self, length: int) -> None:
        """
        TTM_TREND (Trend based on TTM Squeeze)
        """

        column_name = f"TTM_TRND_{length}"

        self.indicators.data.ta.ttm_trend(length=length, append=True)
        if column_name not in self.indicators.data.columns:
            log.debug("Indicator 'Trend -> TTM_TREND' can not be added.")
            return

        self._conditions["TTM_TREND"] = {
            OrderType.BUY: lambda x: x[column_name] == 1,
            OrderType.SELL: lambda x: x[column_name] == -1,
        }

        self._columns_needed += [column_name]

    def _add_vertical_horizontal_filter(self, length: int, length_ema: int) -> None:
        """
        VHF (Vertical Horizontal Filter)
        """

        column_name = f"VHF_{length}_EMA_{length_ema}"

        self.indicators.data[column_name] = self.indicators.data.ta.ema(
            close=self.indicators.data.ta.vhf(length=length),
            length=length_ema,
        )
        if column_name not in self.indicators.data.columns:
            log.debug("Indicator 'Trend -> VHF' can not be added.")
            return

        self._conditions["VHF"] = {
            OrderType.BUY: lambda x: x[column_name] > 0.45,
            OrderType.SELL: lambda x: x[column_name] > 0.4,
        }

        self._columns_needed += [column_name]

    def _add_vortex_indicator(self, length: int) -> None:
        """
        VORTEX (Vortex Indicator)
        """

        column_names = {
            "VTXP": f"VTXP_{length}",
            "VTXM": f"VTXM_{length}",
        }

        self.indicators.data.ta.vortex(length=length, append=True)
        if column_names["VTXP"] not in self.indicators.data.columns:
            log.debug("Indicator 'Trend -> VORTEX' can not be added.")
            return

        self._conditions["VORTEX"] = {
            OrderType.BUY: lambda x: x[column_names["VTXP"]] > x[column_names["VTXM"]],
            OrderType.SELL: lambda x: x[column_names["VTXM"]] < x[column_names["VTXP"]],
        }

        self._columns_needed += column_names.values()

    def _add_parabolic_stop_and_reverse(self, acceleration: float, maximum: float) -> None:
        """
        PSAR (Parabolic Stop and Reverse)
        """

        column_names = {
            "PSARl": f"PSARl_{acceleration}_{maximum}",
            "PSARs": f"PSARs_{acceleration}_{maximum}",
        }

        self.indicators.data.ta.psar(af=acceleration, max_af=maximum, append=True)
        if column_names["PSARl"] not in self.indicators.data.columns:
            log.debug("Indicator 'Trend -> PSAR' can not be added.")
            return

        self._conditions["PSAR"] = {
            OrderType.BUY: lambda x: x["Close"] > x[column_names["PSARl"]],
            OrderType.SELL: lambda x: x["Close"] < x[column_names["PSARs"]],
        }

        self._columns_needed += column_names.values()

    def _add_choppiness_index(self, length: int, length_atr: int, scalar: float) -> None:
        """
        CHOP (Choppiness Index)
        """

        column_name = f"CHOP_{length}_{length_atr}_{scalar}"

        self.indicators.data.ta.chop(length=length, atr_length=length_atr, scalar=scalar, append=True)
        if column_name not in self.indicators.data.columns:
            log.debug("Indicator 'Trend -> CHOP' can not be added.")
            return

        self._conditions["CHOP"] = {
            OrderType.BUY: lambda x: x[column_name] < 61.8,
            OrderType.SELL: lambda x: x[column_name] > 61.8,
        }

        self._columns_needed += [column_name]

    def _add_chande_kroll_stop(self, p: int, x: float, q: int) -> None:
        """
        CKSP (Chande Kroll Stop)

        p (int): ATR and first stop period.
        x (float): ATR scalar.
        q (int): Second stop period.

        # TODO: try p=10, x=1, q=9
        """

        column_names = {
            "CKSPl": f"CKSPl_{p}_{x}_{q}",
            "CKSPs": f"CKSPs_{p}_{x}_{q}",
        }

        self.indicators.data.ta.cksp(p=p, x=x, q=q, append=True)
        if column_names["CKSPl"] not in self.indicators.data.columns:
            log.debug("Indicator 'Trend -> CKSP' can not be added.")
            return

        self._conditions["CKSP"] = {
            OrderType.BUY: lambda x: x[column_names["CKSPl"]] > x[column_names["CKSPs"]],
            OrderType.SELL: lambda x: x[column_names["CKSPl"]] < x[column_names["CKSPs"]],
        }

        self._columns_needed += column_names.values()

    def add_all(self) -> None:
        self._add_trend_intensity_index(length_sma=15, length_signal=5)
        self._add_trend_based_on_ttm_squeeze(length=8)
        self._add_vertical_horizontal_filter(length=30, length_ema=10)
        self._add_vortex_indicator(length=14)
        self._add_parabolic_stop_and_reverse(acceleration=0.02, maximum=0.2)
        self._add_choppiness_index(length=14, length_atr=1, scalar=100.0)
        self._add_chande_kroll_stop(p=10, x=3.0, q=20)

        super().add_all()


class Volume(CategoryBase):
    def _add_price_volume_trend(self, length_sma: int) -> None:
        # TODO: double-check this indicator
        """
        PVT (Price Volume Trend)
        """

        column_names = {
            "PVT": "PVT",
            "PVT_SMA": f"PVT_SMA_{length_sma}",
        }

        self.indicators.data.ta.pvt(append=True)
        self.indicators.data[column_names["PVT_SMA"]] = self.indicators.data.ta.sma(close="PVT", length=length_sma)
        if column_names["PVT"] not in self.indicators.data.columns:
            log.debug("Indicator 'Volume -> PVT' can not be added.")
            return

        self._conditions["PVT"] = {
            OrderType.BUY: lambda x: x[column_names["PVT_SMA"]] < x["PVT"],
            OrderType.SELL: lambda x: x[column_names["PVT_SMA"]] > x["PVT"],
        }

        self._columns_needed += column_names.values()

    def _add_accumulation_distribution_oscillator(self, fast: int, slow: int) -> None:
        # TODO: double-check this indicator
        """
        ADOSC (Accumulation/Distribution Oscillator)
        """
        column_name = "ADOSC_direction"

        self.indicators.data[column_name] = (
            self.indicators.data.ta.adosc(fast=fast, slow=slow).rolling(2).apply(lambda x: x.iloc[1] > x.iloc[0])
        )
        if column_name not in self.indicators.data.columns:
            log.debug("Indicator 'Volume -> ADOSC' can not be added.")
            return

        self._conditions["ADOSC"] = {
            OrderType.BUY: lambda x: x[column_name] == 1,
            OrderType.SELL: lambda x: x[column_name] == 0,
        }

        self._columns_needed += [column_name]

    def _add_chaikin_money_flow(self, length: int) -> None:
        """
        CMF (Chaikin Money Flow)
        """

        column_name = f"CMF_{length}"

        self.indicators.data.ta.cmf(length=length, append=True)
        if column_name not in self.indicators.data.columns:
            log.debug("Indicator 'Volume -> CMF' can not be added.")
            return

        cmf = {"max": self.indicators.data[column_name].max(), "min": self.indicators.data[column_name].min()}
        self._conditions["CMF"] = {
            OrderType.BUY: lambda x: x[column_name] > cmf["max"] * 0.2,
            OrderType.SELL: lambda x: x[column_name] < cmf["min"] * 0.2,
        }

        self._columns_needed += [column_name]

    def _add_elders_force_index(self, length: int, mamode: str) -> None:
        """
        EFI (Elder's Force Index)
        """

        column_name = f"EFI_{length}"

        self.indicators.data.ta.efi(length=length, mamode=mamode, append=True)
        if column_name not in self.indicators.data.columns:
            log.debug("Indicator 'Volume -> EFI' can not be added.")
            return

        self._conditions["EFI"] = {
            OrderType.BUY: lambda x: x[column_name] < 0,
            OrderType.SELL: lambda x: x[column_name] > 0,
        }

        self._columns_needed += [column_name]

    def _add_klinger_volume_oscillator(self, fast: int, slow: int, signal: int) -> None:
        """
        KVO (Klinger Volume Oscillator)
        """

        column_names = {
            "KVO": f"KVO_{fast}_{slow}_{signal}",
            "KVOs": f"KVOs_{fast}_{slow}_{signal}",
        }

        self.indicators.data.ta.kvo(fast=fast, slow=slow, signal=signal, mamode="ema", append=True)
        if column_names["KVO"] not in self.indicators.data.columns:
            log.debug("Indicator 'Volume -> KVO' can not be added.")
            return

        self._conditions["KVO"] = {
            OrderType.BUY: lambda x: x[column_names["KVO"]] > x[column_names["KVOs"]],
            OrderType.SELL: lambda x: x[column_names["KVO"]] < x[column_names["KVOs"]],
        }

        self._columns_needed += column_names.values()

    def add_all(self) -> None:
        self._add_price_volume_trend(length_sma=9)
        self._add_accumulation_distribution_oscillator(fast=30, slow=45)
        self._add_chaikin_money_flow(length=20)
        self._add_elders_force_index(length=13, mamode="ema")
        self._add_klinger_volume_oscillator(fast=34, slow=55, signal=13)

        super().add_all()


class Volatility(CategoryBase):
    def _add_starc_bands(self, length_sma: int, length_atr: int, multiplier_atr: float) -> None:
        """
        STARC (Stoller Average Range Channel)
        https://www.investopedia.com/terms/s/starc.asp
        """

        column_names = {
            "STARC_U": f"STARC_U_{length_sma}_{length_atr}_{multiplier_atr}",
            "STARC_B": f"STARC_B_{length_sma}_{length_atr}_{multiplier_atr}",
        }

        sma = self.indicators.data.ta.sma(length=length_sma)
        atr = self.indicators.data.ta.atr(length=length_atr)

        self.indicators.data[column_names["STARC_U"]] = sma + multiplier_atr * atr
        self.indicators.data[column_names["STARC_B"]] = sma - multiplier_atr * atr

        self._conditions["STARC"] = {
            OrderType.BUY: lambda x: x["Close"] < x[column_names["STARC_B"]],
            OrderType.SELL: lambda x: x["Close"] > x[column_names["STARC_U"]],
        }

        self._columns_needed += column_names.values()

    def _add_mass_index(self, fast: int, slow: int) -> None:
        """
        MASSI (Mass Index)
        https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/mass-index#introduction
        """

        column_name = f"MASSI_{fast}_{slow}"

        self.indicators.data.ta.massi(fast=fast, slow=slow, append=True)
        if column_name not in self.indicators.data.columns:
            log.debug("Indicator 'Volatility -> MASSI' can not be added.")
            return

        self._conditions["MASSI"] = {
            OrderType.BUY: lambda x: 26 < x[column_name] < 27,
            OrderType.SELL: lambda x: 26 < x[column_name] < 27,
        }

        self._columns_needed += [column_name]

    def _add_holt_winter_channel(self, na: float, nb: float, nc: float, nd: float, scalar: float) -> None:
        """
        HWC (Holt-Winter Channel)
        https://www.mql5.com/en/code/20857
        """

        column_name = "HWM"

        self.indicators.data.ta.hwc(na=na, nb=nb, nc=nc, nd=nd, scalar=scalar, append=True)
        if column_name not in self.indicators.data.columns:
            log.debug("Indicator 'Volatility -> HWC' can not be added.")
            return

        self._conditions["HWC"] = {
            OrderType.BUY: lambda x: x["Close"] > x[column_name],
            OrderType.SELL: lambda x: x["Close"] < x[column_name],
        }

        self._columns_needed += [column_name]

    def _add_bollinger_bands(self, length: int, std: float) -> None:
        """
        BBANDS (Bollinger Bands)
        """
        column_names = {"BBL": f"BBL_{length}_{std}", "BBU": f"BBU_{length}_{std}"}

        self.indicators.data.ta.bbands(length=length, std=std, append=True)
        if column_names["BBL"] not in self.indicators.data.columns:
            log.debug("Indicator 'Volatility -> BBANDS' can not be added.")
            return

        self._conditions["BBANDS"] = {
            OrderType.BUY: lambda x: x["Close"] > x[column_names["BBL"]],
            OrderType.SELL: lambda x: x["Close"] < x[column_names["BBU"]],
        }

        self._columns_needed += column_names.values()

    def _add_acceleration_bands(self, length: int, c: int, mamode: str) -> None:
        # TODO: double-check this indicator
        """
        ACCBANDS (Acceleration Bands)
        https://trendspider.com/learning-center/getting-started-with-acceleration-bands-in-technical-analysis/
        """

        column_names = {
            "ACCBU": f"ACCBU_{length}",
            "ACCBM": f"ACCBM_{length}",
            "ACCBL": f"ACCBL_{length}",
        }

        self.indicators.data.ta.accbands(length=length, c=c, mamode=mamode, append=True)
        if column_names["ACCBM"] not in self.indicators.data.columns:
            log.debug("Indicator 'Volatility -> ACCBANDS' can not be added.")
            return

        self._conditions["ACCBANDS"] = {
            OrderType.BUY: lambda x: x["Close"] > x[column_names["ACCBM"]],
            OrderType.SELL: lambda x: x["Close"] < x[column_names["ACCBM"]],
        }

        self._columns_needed += column_names.values()

    def add_all(self) -> None:
        self._add_starc_bands(length_sma=6, length_atr=14, multiplier_atr=1.5)
        self._add_mass_index(fast=9, slow=25)
        self._add_holt_winter_channel(na=0.2, nb=0.1, nc=0.1, nd=0.1, scalar=1)
        self._add_bollinger_bands(length=20, std=2.0)
        self._add_acceleration_bands(length=20, c=4, mamode="sma")

        super().add_all()


class Cycles(CategoryBase):
    def _add_even_better_sinewave(self, length: int, bars: int) -> None:
        """
        EBSW (Even Better Sinewave)
        https://www.prorealcode.com/prorealtime-indicators/even-better-sinewave/
        """

        column_name = f"EBSW_{length}_{bars}"

        self.indicators.data.ta.ebsw(length=length, bars=bars, append=True)
        if column_name not in self.indicators.data.columns:
            log.debug("Indicator 'Cycles -> EBSW' can not be added.")
            return

        self._conditions["EBSW"] = {
            OrderType.BUY: lambda x: x[column_name] > 0.5,
            OrderType.SELL: lambda x: x[column_name] < -0.5,
        }

        self._columns_needed += [column_name]

    def add_all(self) -> None:
        self._add_even_better_sinewave(length=40, bars=10)

        super().add_all()


class Candle(CategoryBase):
    def _add_heikin_ashi(self) -> None:
        """
        HA (Heikin-Ashi)
        """

        column_names = {
            "HA_open": "HA_open",
            "HA_close": "HA_close",
            "HA_low": "HA_low",
            "HA_high": "HA_high",
        }

        self.indicators.data.ta.ha(append=True)
        if column_names["HA_open"] not in self.indicators.data.columns:
            log.debug("Indicator 'Candle -> HA' can not be added.")
            return

        self._conditions["HA"] = {
            OrderType.BUY: lambda x: (x["HA_open"] < x["HA_close"]) and (x["HA_low"] == x["HA_open"]),
            OrderType.SELL: lambda x: (x["HA_open"] > x["HA_close"]) and (x["HA_high"] == x["HA_open"]),
        }

        self._columns_needed += column_names.values()

    def add_all(self) -> None:
        self._add_heikin_ashi()

        super().add_all()


class Overlap(CategoryBase):
    def _add_2dema(self, length_short: int, length_long: int) -> None:
        """
        2DEMA (Trend direction by Double EMA)
        """

        column_names = {
            "DEMA_short": f"DEMA_{length_short}",
            "DEMA_long": f"DEMA_{length_long}",
            "2DEMA": "2DEMA",
        }

        self.indicators.data.ta.dema(length=length_short, append=True)
        self.indicators.data.ta.dema(length=length_long, append=True)
        self.indicators.data[column_names["2DEMA"]] = self.indicators.data.apply(
            lambda x: 1 if x[column_names["DEMA_short"]] >= x[column_names["DEMA_long"]] else -1,
            axis=1,
        )

        if column_names["2DEMA"] not in self.indicators.data.columns:
            log.debug("Indicator 'Overlap -> 2DEMA' can not be added.")
            return

        self._conditions["2DEMA"] = {
            OrderType.BUY: lambda x: x[column_names["2DEMA"]] == 1,
            OrderType.SELL: lambda x: x[column_names["2DEMA"]] == -1,
        }

        self._columns_needed += column_names.values()

    def _add_gann_high_low_activator(self, length_high: int, length_low: int, mamode: str) -> None:
        """
        GHLA (Gann High-Low Activator)
        https://www.sierrachart.com/index.php?page=doc/StudiesReference.php&ID=447&Name=Gann_HiLo_Activator
        https://www.tradingview.com/script/XNQSLIYb-Gann-High-Low/
        """

        column_name = f"HILO_{length_high}_{length_low}"

        self.indicators.data.ta.hilo(high_length=length_high, low_length=length_low, mamode=mamode, append=True)
        if column_name not in self.indicators.data.columns:
            log.debug("Indicator 'Overlap -> GHLA' can not be added.")
            return

        self._conditions["GHLA"] = {
            OrderType.BUY: lambda x: x["Close"] > x[column_name],
            OrderType.SELL: lambda x: x["Close"] < x[column_name],
        }

        self._columns_needed += [column_name]

    def _add_linear_regression(self, length: int) -> None:
        """
        LINREG (Linear Regression)
        """

        column_name = f"LRr_{length}"

        self.indicators.data.ta.linreg(length=length, r=True, append=True)
        if column_name not in self.indicators.data.columns:
            log.debug("Indicator 'Overlap -> LINREG' can not be added.")
            return

        self.indicators.data["LRr_direction"] = (
            self.indicators.data[column_name].rolling(2).apply(lambda x: x.iloc[1] > x.iloc[0])
        )

        self._conditions["LINREG"] = {
            OrderType.BUY: lambda x: x["LRr_direction"] == 1,
            OrderType.SELL: lambda x: x["LRr_direction"] == 0,
        }

        self._columns_needed += ["LRr_direction"]

    def add_all(self) -> None:
        self._add_2dema(length_short=15, length_long=30)
        self._add_gann_high_low_activator(length_high=13, length_low=21, mamode="sma")
        self._add_linear_regression(length=14)

        super().add_all()


class Momentum(CategoryBase):
    def _add_schaff_trend_cycle(self, tclength: int, fast: int, slow: int, factor: float) -> None:
        """
        STC (Schaff Trend Cycle)
        https://www.prorealcode.com/prorealtime-indicators/schaff-trend-cycle2/
        """

        column_name = f"STC_{tclength}_{fast}_{slow}_{factor}"

        self.indicators.data.ta.stc(tclength=tclength, fast=fast, slow=slow, factor=factor, append=True)
        if column_name not in self.indicators.data.columns:
            log.debug("Indicator 'Momentum -> STC' can not be added.")
            return

        self._conditions["STC"] = {
            OrderType.BUY: lambda x: x[column_name] < 75,
            OrderType.SELL: lambda x: x[column_name] > 25,
        }

        self._columns_needed += [column_name]

    def _add_ultimate_oscillator(
        self,
        fast: int,
        medium: int,
        slow: int,
        fast_weight: float,
        medium_weight: float,
        slow_weight: float,
    ) -> None:
        """
        UO (Ultimate Oscillator)
        https://www.tradingview.com/support/solutions/43000502328-ultimate-oscillator-uo/
        """

        column_name = f"UO_{fast}_{medium}_{slow}"

        self.indicators.data.ta.uo(
            fast=fast,
            medium=medium,
            slow=slow,
            fast_w=fast_weight,
            medium_w=medium_weight,
            slow_w=slow_weight,
            append=True,
        )
        if column_name not in self.indicators.data.columns:
            log.debug("Indicator 'Momentum -> UO' can not be added.")
            return

        self._conditions["UO"] = {
            OrderType.BUY: lambda x: x[column_name] < 30,
            OrderType.SELL: lambda x: x[column_name] > 65,
        }

        self._columns_needed += [column_name]

    def _add_commodity_channel_index(self, length: int, c: float) -> None:
        """
        CCI (Commodity Channel Index)
        https://www.tradingview.com/support/solutions/43000502001-commodity-channel-index-cci/
        """

        column_name = f"CCI_{length}_{c}"

        self.indicators.data.ta.cci(length=length, c=c, append=True)
        if column_name not in self.indicators.data.columns:
            log.debug("Indicator 'Momentum -> CCI' can not be added.")
            return

        self.indicators.data["CCI_direction"] = (
            self.indicators.data[column_name].rolling(2).apply(lambda x: x.iloc[1] > x.iloc[0])
        )

        self._conditions["CCI"] = {
            OrderType.BUY: lambda x: x[column_name] < -100 and x["CCI_direction"] == 1,
            OrderType.SELL: lambda x: x[column_name] > 100 and x["CCI_direction"] == 0,
        }

        self._columns_needed += [column_name, "CCI_direction"]

    def _add_relative_vigor_index(self, length: int, length_swma: int) -> None:
        """
        RVGI (Relative Vigor Index)
        https://www.investopedia.com/terms/r/relative_vigor_index.asp
        """

        column_names = {
            "RVGI": f"RVGI_{length}_{length_swma}",
            "RVGIs": f"RVGIs_{length}_{length_swma}",
        }

        self.indicators.data.ta.rvgi(length=length, swma_length=length_swma, append=True)
        if column_names["RVGI"] not in self.indicators.data.columns:
            log.debug("Indicator 'Momentum -> RVGI' can not be added.")
            return

        self._conditions["RVGI"] = {
            OrderType.BUY: lambda x: x[column_names["RVGI"]] > x[column_names["RVGIs"]],
            OrderType.SELL: lambda x: x[column_names["RVGI"]] < x[column_names["RVGIs"]],
        }

        self._columns_needed += column_names.values()

    def _add_macd(self, fast: int, slow: int, signal: int) -> None:
        """
        MACD (Moving Average Convergence Divergence)
        """

        column_names = {
            "MACD": f"MACD_{fast}_{slow}_{signal}",
            "MACDh": f"MACDh_{fast}_{slow}_{signal}",
            "MACDs": f"MACDs_{fast}_{slow}_{signal}",
        }

        self.indicators.data.ta.macd(fast=fast, slow=slow, signal=signal, append=True)
        if column_names["MACD"] not in self.indicators.data.columns:
            log.debug("Indicator 'Momentum -> MACD' can not be added.")
            return

        self.indicators.data["MACD_ma_diff"] = (
            self.indicators.data[column_names["MACDh"]].rolling(2).apply(lambda x: x.iloc[1] > x.iloc[0])
        )

        self._conditions["MACD"] = {
            OrderType.BUY: lambda x: x["MACD_ma_diff"] == 1,
            OrderType.SELL: lambda x: x["MACD_ma_diff"] == 0,
        }

        self._columns_needed += column_names.values()

    def _add_stochastic_oscillator(self, k: int, d: int, smooth_k: int, mamode: str) -> None:
        """
        STOCH (Stochastic Oscillator)
        """

        column_names = {
            "STOCHk": f"STOCHk_{k}_{d}_{smooth_k}",
            "STOCHd": f"STOCHd_{k}_{d}_{smooth_k}",
        }

        self.indicators.data.ta.stoch(k=k, d=d, smooth_k=smooth_k, mamode=mamode, append=True)
        if column_names["STOCHk"] not in self.indicators.data.columns:
            log.debug("Indicator 'Momentum -> STOCH' can not be added.")
            return

        self._conditions["STOCH"] = {
            OrderType.BUY: lambda x: x[column_names["STOCHd"]] < 80 and x[column_names["STOCHk"]] < 80,
            OrderType.SELL: lambda x: x[column_names["STOCHd"]] > 20 and x[column_names["STOCHk"]] > 20,
        }

        self._columns_needed += column_names.values()

    def add_all(self) -> None:
        self._add_schaff_trend_cycle(tclength=10, fast=12, slow=26, factor=0.5)
        self._add_ultimate_oscillator(fast=10, medium=15, slow=30, fast_weight=4.0, medium_weight=2.0, slow_weight=1.0)
        self._add_commodity_channel_index(length=14, c=0.015)
        self._add_relative_vigor_index(length=14, length_swma=4)
        self._add_macd(fast=8, slow=21, signal=5)
        self._add_stochastic_oscillator(k=14, d=3, smooth_k=3, mamode="sma")

        super().add_all()
