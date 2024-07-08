from typing import Dict

from data.settings import DATA_COLUMNS
from services.ta.indicators import Cycles, Momentum, Overlap, Trend, Volatility, Volume
from services.ta.indicators.models import Indicator
from utils.logger import get_logger

log = get_logger()


def get_indicators(data) -> Dict[str, Dict[str, Indicator]]:
    indicators = dict()

    trend = Trend(data)
    trend.add_trend_intensity_index(length_sma=20, length_signal=5)  # TII
    trend.add_average_directional_movement(length=14, lensig=14, mamode="rma")  # ADX
    trend.add_chande_kroll_stop(p=10, x=1.0, q=9)  # CKSP
    trend.add_parabolic_stop_and_reverse(acceleration=0.02, maximum=0.2)  # PSAR
    trend.add_choppiness_index(length=14, length_atr=1, scalar=100.0)  # CHOP
    # trend.add_vertical_horizontal_filter(length=18, length_ema=6)  # VHF (exit)

    overlap = Overlap(data)
    overlap.add_gann_high_low_activator(length_high=13, length_low=21, mamode="dema")  # GHLA
    overlap.add_linear_regression(length=14)  # LINREG

    momentum = Momentum(data)
    momentum.add_macd_dema(length_fast=10, length_slow=20)  # MACD_DEMA
    momentum.add_schaff_trend_cycle(tclength=10, fast=23, slow=50, factor=0.4)  # STC
    momentum.add_commodity_channel_index(length=14, c=0.015)  # CCI
    momentum.add_relative_vigor_index(length=14, length_swma=4)  # RVI
    momentum.add_stochastic_oscillator(k=14, d=3, smooth_k=3, mamode="dema")  # STOCH

    cycles = Cycles(data)
    cycles.add_even_better_sinewave(length=40, bars=10)  # EBSW

    volatility = Volatility(data)
    volatility.add_starc_bands(length_sma=6, length_atr=15, multiplier_atr=1.5)  # STARC
    volatility.add_mass_index(fast=9, slow=25)  # MASSI
    volatility.add_bollinger_bands(length=14, std=1.8)  # BBANDS
    volatility.add_acceleration_bands(length=20, c=3, mamode="dema")  # ACCBANDS

    volume = Volume(data)
    volume.add_price_volume_trend(drift=2, length_sma=14)  # PVT
    volume.add_accumulation_distribution_oscillator(fast=6, slow=20)  # ADOSC
    volume.add_chaikin_money_flow(length=21)  # CMF
    volume.add_klinger_volume_oscillator(fast=34, slow=55, signal=13, mamode="dema")  # KVO

    columns_keep = set(DATA_COLUMNS)
    for category in [trend, volatility, volume, cycles, overlap, momentum]:
        for indicator in category.indicators.values():
            columns_keep |= set(indicator.columns)

        indicators[category.__class__.__name__] = category.indicators

    data.drop(columns=list(set(data.columns) - columns_keep), inplace=True)

    return indicators
