from typing import Dict, List, Optional, Tuple

from pydantic import Field

from data.settings import DATA_COLUMNS
from services.ta.indicators import Cycles, Momentum, Overlap, Trend, Volatility, Volume
from services.ta.indicators.models import Indicator
from services.ta.strategies import compose_strategies_list, dump_strategies_in_file, get_top_strategies
from services.ta.strategies.models import ComposeStrategiesListMethod, Strategy
from utils.logger import get_logger

log = get_logger()


def get_indicators(data, **kwargs) -> Dict[str, Dict[str, Indicator]]:
    indicators_mapping = dict()

    trend = Trend(data)
    trend.add_trend_intensity_index(length_sma=20, length_signal=5)  # TII
    trend.add_average_directional_movement(length=14, lensig=14, mamode="rma")  # ADX
    trend.add_parabolic_stop_and_reverse(acceleration=0.01, maximum=0.2)  # PSAR
    trend.add_choppiness_index(length=14, length_atr=2, scalar=80.0)  # CHOP

    overlap = Overlap(data)
    overlap.add_linear_regression(length=8, limit=0.3)  # LINREG
    overlap.add_supertrend(length=7, multiplier=3.0)  # SUPERTREND

    momentum = Momentum(data)
    momentum.add_macd_dema(length_fast=10, length_slow=20)  # MACD_DEMA
    momentum.add_schaff_trend_cycle(tclength=10, fast=23, slow=45, factor=0.55)  # STC
    momentum.add_commodity_channel_index(length=16, c=0.02)  # CCI
    momentum.add_relative_vigor_index(length=14, length_swma=4)  # RVI
    momentum.add_stochastic_oscillator(k=10, d=3, smooth_k=2, mamode="dema")  # STOCH

    cycles = Cycles(data)
    cycles.add_even_better_sinewave(length=40, bars=14)  # EBSW

    volatility = Volatility(data)
    volatility.add_starc_bands(length_sma=10, length_atr=15, multiplier_atr=2.0)  # STARC
    volatility.add_mass_index(fast=9, slow=25)  # MASSI
    volatility.add_bollinger_bands(length=22, std=2.0)  # BBANDS
    volatility.add_acceleration_bands(length=14, c=1, mamode="dema")  # ACCBANDS

    volume = Volume(data)
    volume.add_price_volume_trend(drift=12, length_sma=30)  # PVT
    volume.add_accumulation_distribution_oscillator(fast=6, slow=14)  # ADOSC
    volume.add_chaikin_money_flow(length=26)  # CMF
    volume.add_klinger_volume_oscillator(fast=11, slow=35, signal=18, mamode="ema")  # KVO

    columns_keep = set(DATA_COLUMNS)
    for category in [trend, volatility, volume, cycles, overlap, momentum]:
        for indicator in category.indicators.values():
            columns_keep |= set(indicator.columns)

        indicators_mapping[category.__class__.__name__] = category.indicators

    data.drop(columns=list(set(data.columns) - columns_keep), inplace=True)

    return indicators_mapping


def get_strategies(
    compose_strategies_list_method: ComposeStrategiesListMethod,
    indicators_mapping: Dict[str, Dict[str, Indicator]],
    indicators_selector: List[Tuple[str, str]] = Field(default_factory=list),
    old_strategies_file_name: Optional[str] = None,
) -> List[Strategy]:
    return compose_strategies_list(
        compose_strategies_list_method,
        indicators_mapping,
        indicators_selector,
        old_strategies_file_name,
    )


def read_top_strategies(indicators_mapping: Dict[str, Dict[str, Indicator]], strategies_file_name: str) -> List[Strategy]:
    return get_top_strategies(indicators_mapping, strategies_file_name)


def save_strategies(strategies: List[Strategy], new_strategies_file_name: Optional[str]) -> None:
    if not new_strategies_file_name:
        return

    return dump_strategies_in_file(strategies, new_strategies_file_name)
