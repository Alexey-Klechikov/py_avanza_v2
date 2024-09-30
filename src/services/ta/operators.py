from typing import Dict, List, Optional

from services.ta.indicators import Cycles, Momentum, Overlap, Trend, Volatility, Volume
from services.ta.indicators.models import Indicator
from services.ta.strategies import compose_strategies_list, dump_strategies_in_file, get_top_strategies
from services.ta.strategies.models import ComposeStrategiesListMethod, Strategy
from utils.logger import get_logger

log = get_logger()


def get_indicators(data, settings, **kwargs) -> Dict[str, Dict[str, Indicator]]:
    indicators_mapping = dict()

    trend = Trend(data)
    trend.add_trend_intensity_index(**settings.INDICATORS.get("Trend", {}).get("TII", {}))
    trend.add_average_directional_movement(**settings.INDICATORS.get("Trend", {}).get("ADX", {}))
    trend.add_parabolic_stop_and_reverse(**settings.INDICATORS.get("Trend", {}).get("PSAR", {}))
    trend.add_choppiness_index(**settings.INDICATORS.get("Trend", {}).get("CHOP", {}))

    overlap = Overlap(data)
    overlap.add_linear_regression(**settings.INDICATORS.get("Overlap", {}).get("LINREG", {}))
    overlap.add_supertrend(**settings.INDICATORS.get("Overlap", {}).get("SUPERTREND", {}))

    momentum = Momentum(data)
    momentum.add_macd_dema(**settings.INDICATORS.get("Momentum", {}).get("MACD_DEMA", {}))
    momentum.add_schaff_trend_cycle(**settings.INDICATORS.get("Momentum", {}).get("STC", {}))
    momentum.add_commodity_channel_index(**settings.INDICATORS.get("Momentum", {}).get("CCI", {}))
    momentum.add_relative_vigor_index(**settings.INDICATORS.get("Momentum", {}).get("RVGI", {}))
    momentum.add_stochastic_oscillator(**settings.INDICATORS.get("Momentum", {}).get("STOCH", {}))

    cycles = Cycles(data)
    cycles.add_even_better_sinewave(**settings.INDICATORS.get("Cycles", {}).get("EBSW", {}))

    volatility = Volatility(data)
    volatility.add_starc_bands(**settings.INDICATORS.get("Volatility", {}).get("STARC", {}))
    volatility.add_mass_index(**settings.INDICATORS.get("Volatility", {}).get("MASSI", {}))
    volatility.add_bollinger_bands(**settings.INDICATORS.get("Volatility", {}).get("BBANDS", {}))
    volatility.add_acceleration_bands(**settings.INDICATORS.get("Volatility", {}).get("ACCBANDS", {}))

    volume = Volume(data)
    volume.add_price_volume_trend(**settings.INDICATORS.get("Volume", {}).get("PVT", {}))
    volume.add_accumulation_distribution_oscillator(**settings.INDICATORS.get("Volume", {}).get("ADOSC", {}))
    volume.add_chaikin_money_flow(**settings.INDICATORS.get("Volume", {}).get("CMF", {}))
    volume.add_klinger_volume_oscillator(**settings.INDICATORS.get("Volume", {}).get("KVO", {}))

    columns_keep = {"Open", "High", "Low", "Close", "Volume"}
    for category in [trend, volatility, volume, cycles, overlap, momentum]:
        for indicator in category.indicators.values():
            columns_keep |= set(indicator.columns)

        indicators_mapping[category.__class__.__name__] = category.indicators

    data.drop(columns=list(set(data.columns) - columns_keep), inplace=True)

    return indicators_mapping


def get_strategies(
    compose_strategies_list_method: ComposeStrategiesListMethod,
    indicators_mapping: Dict[str, Dict[str, Indicator]],
    old_strategies_file_name: Optional[str] = None,
) -> List[Strategy]:
    return compose_strategies_list(
        compose_strategies_list_method,
        indicators_mapping,
        old_strategies_file_name,
    )


def read_top_strategies(indicators_mapping: Dict[str, Dict[str, Indicator]], strategies_file_name: str) -> List[Strategy]:
    return get_top_strategies(indicators_mapping, strategies_file_name)


def save_strategies(strategies: List[Strategy], new_strategies_file_name: Optional[str]) -> None:
    if not new_strategies_file_name:
        return

    return dump_strategies_in_file(strategies, new_strategies_file_name)
