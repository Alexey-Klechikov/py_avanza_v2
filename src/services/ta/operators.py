from typing import List

import pandas as pd

from data.settings import DATA_COLUMNS
from services.ta.figure import Figure
from services.ta.indicators import Cycles, Momentum, Overlap, Trend, Volatility, Volume
from services.ta.indicators.models import Plots


def get_indicators(data) -> dict:
    indicators = dict()

    cycles = Cycles(data)
    cycles.add_even_better_sinewave(length=40, bars=10)

    momentum = Momentum(data)
    momentum.add_schaff_trend_cycle(tclength=10, fast=12, slow=26, factor=0.5)  # STC
    momentum.add_ultimate_oscillator(
        fast=10,
        medium=15,
        slow=30,
        fast_weight=4.0,
        medium_weight=2.0,
        slow_weight=1.0,
    )  # UO
    momentum.add_commodity_channel_index(length=14, c=0.015)  # CCI
    momentum.add_relative_vigor_index(length=14, length_swma=4)  # RVI
    momentum.add_macd(fast=8, slow=21, signal=5)  # MACD
    momentum.add_stochastic_oscillator(k=14, d=3, smooth_k=3, mamode="sma")  # STOCH

    overlap = Overlap(data)
    overlap.add_2dema(length_short=15, length_long=30)  # 2DEMA
    overlap.add_gann_high_low_activator(length_high=13, length_low=21, mamode="sma")  # GHLA
    overlap.add_linear_regression(length=14)  # LINREG

    trend = Trend(data)
    trend.add_trend_intensity_index(length_sma=15, length_signal=5)  # TII
    trend.add_trend_based_on_ttm_squeeze(length=8)  # TTM_TREND
    trend.add_vertical_horizontal_filter(length=30, length_ema=10)  # VHF
    trend.add_vortex_indicator(length=14)  # VORTEX
    trend.add_parabolic_stop_and_reverse(acceleration=0.02, maximum=0.2)  # PSAR
    trend.add_choppiness_index(length=14, length_atr=1, scalar=100.0)  # CHOP
    trend.add_chande_kroll_stop(p=10, x=3.0, q=20)  # CKSP

    volatility = Volatility(data)
    volatility.add_starc_bands(length_sma=6, length_atr=14, multiplier_atr=1.5)  # STARC
    volatility.add_mass_index(fast=9, slow=25)  # MASSI
    volatility.add_holt_winter_channel(na=0.2, nb=0.1, nc=0.1, nd=0.1, scalar=1)  # HWC
    volatility.add_bollinger_bands(length=20, std=2.0)  # BBANDS
    volatility.add_acceleration_bands(length=20, c=4, mamode="sma")  # ACCBANDS

    volume = Volume(data)
    volume.add_price_volume_trend(length_sma=9)  # PVT
    volume.add_accumulation_distribution_oscillator(fast=30, slow=45)  # ADOSC
    volume.add_chaikin_money_flow(length=20)  # CMF
    volume.add_elders_force_index(length=13, mamode="ema")  # EFI
    volume.add_klinger_volume_oscillator(fast=34, slow=55, signal=13)  # KVO

    columns_keep = set(DATA_COLUMNS)
    for category in [trend, volatility, volume, cycles, overlap, momentum]:
        for indicator in category.indicators.values():
            columns_keep |= set(indicator.columns)

        indicators[category.__class__.__name__] = category.indicators

    data.drop(columns=list(set(data.columns) - columns_keep), inplace=True)

    return indicators


def plot_indicators(data: pd.DataFrame, indicators_plots: List[Plots]):
    figure = Figure(data=data)

    for plots in indicators_plots:
        figure.add_plot(plots)

    figure.show()
