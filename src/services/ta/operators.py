from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from data.settings import DATA_COLUMNS
from services.ta.figure import Figure
from services.ta.indicators import Cycles, Momentum, Overlap, Trend, Volatility, Volume
from services.ta.indicators.models import Indicator, Panel, Plot, Plots
from utils.logger import get_logger

log = get_logger()


def get_indicators(data) -> Dict[str, Dict[str, Indicator]]:
    indicators = dict()

    trend = Trend(data)
    trend.add_trend_intensity_index(length_sma=20, length_signal=5)  # TII (buy / sell)
    trend.add_average_directional_movement(length=14, lensig=14, mamode="rma")  # ADX (exit | buy / sell)
    trend.add_chande_kroll_stop(p=10, x=1.0, q=9)  # CKSP (stop Loss)
    trend.add_parabolic_stop_and_reverse(acceleration=0.02, maximum=0.2)  # PSAR (buy / sell)
    trend.add_choppiness_index(length=14, length_atr=1, scalar=100.0)  # CHOP (exit)
    # trend.add_vertical_horizontal_filter(length=18, length_ema=6)  # VHF (exit)

    overlap = Overlap(data)
    overlap.add_gann_high_low_activator(length_high=13, length_low=21, mamode="dema")  # GHLA (buy / sell)
    overlap.add_linear_regression(length=14)  # LINREG (buy / sell)

    momentum = Momentum(data)
    momentum.add_macd_dema(length_fast=10, length_slow=20)  # MACD_DEMA (buy / sell)
    momentum.add_schaff_trend_cycle(tclength=10, fast=23, slow=50, factor=0.4)  # STC (buy / sell)
    momentum.add_commodity_channel_index(length=14, c=0.015)  # CCI (buy / sell)
    momentum.add_relative_vigor_index(length=14, length_swma=4)  # RVI (buy / sell)
    momentum.add_stochastic_oscillator(k=14, d=3, smooth_k=3, mamode="dema")  # STOCH (buy / sell)

    cycles = Cycles(data)
    cycles.add_even_better_sinewave(length=40, bars=10)  # (buy / sell) -> only use for confirmation

    volatility = Volatility(data)
    volatility.add_starc_bands(length_sma=6, length_atr=15, multiplier_atr=1.5)  # STARC (buy / sell)
    volatility.add_mass_index(fast=9, slow=25)  # MASSI (buy / sell) -> only use as a filter
    volatility.add_bollinger_bands(length=14, std=1.8)  # BBANDS (buy / sell)
    volatility.add_acceleration_bands(length=20, c=3, mamode="dema")  # ACCBANDS (buy / sell | exit?)

    volume = Volume(data)
    volume.add_price_volume_trend(drift=2, length_sma=14)  # PVT (buy / sell)
    volume.add_accumulation_distribution_oscillator(fast=6, slow=20)  # ADOSC (buy / sell)
    volume.add_chaikin_money_flow(length=21)  # CMF (buy / sell | exit)
    volume.add_klinger_volume_oscillator(fast=34, slow=55, signal=13, mamode="dema")  # KVO (buy / sell)

    columns_keep = set(DATA_COLUMNS)
    for category in [trend, volatility, volume, cycles, overlap, momentum]:
        for indicator in category.indicators.values():
            columns_keep |= set(indicator.columns)

        indicators[category.__class__.__name__] = category.indicators

    data.drop(columns=list(set(data.columns) - columns_keep), inplace=True)

    return indicators


def plot_indicators(
    data: pd.DataFrame,
    indicators: Dict[str, Dict[str, Indicator]],
    indicators_to_plot_mapping: List[Tuple[str, str]],
    show_signals: bool = False,
):
    indicators_to_plot = []
    for category, name in indicators_to_plot_mapping:
        indicator = indicators.get(category, {}).get(name)
        if not indicator:
            log.warning(f"Indicator {name} from category {category} does not exist.")
            continue

        if indicator.plots is None:
            log.warning(f"Indicator {name}-{category} does not have any plots.")
            continue

        indicators_to_plot.append(indicator)

    figure = Figure(data=data)
    for indicator in indicators_to_plot:
        figure.add_plot(indicator.plots)

    if show_signals:
        data["buy"] = data["High"]
        data["sell"] = data["Low"]

        for indicator in indicators_to_plot:
            data["buy"] = data.apply(lambda x: x["buy"] if indicator.signal.BUY(x) else np.nan, axis=1)  # type: ignore
            data["sell"] = data.apply(lambda x: x["sell"] if indicator.signal.SELL(x) else np.nan, axis=1)  # type: ignore

        for column in ["buy", "sell"]:
            for non_trading_time in (["09:00", "10:00"], ["17:15", "17:30"]):
                data.loc[data.between_time(non_trading_time[0], non_trading_time[1]).index, column] = np.nan

        plot_signals = Plots(
            panel=Panel.MAIN,
            list=[
                Plot(columns=[column], type="scatter", color=color, markersize=50)
                for column, color in [("buy", "green"), ("sell", "red")]
                if not data[column].isnull().all()
            ],
        )

        figure.add_plot(plot_signals)

    figure.show()
