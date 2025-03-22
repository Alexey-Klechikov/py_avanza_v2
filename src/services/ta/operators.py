from config import SETTINGS
from services.ta.indicators.cycles import Cycles
from services.ta.indicators.models.indicator import Indicator
from services.ta.indicators.momentum import Momentum
from services.ta.indicators.overlap import Overlap
from services.ta.indicators.trend import Trend
from services.ta.indicators.volatility import Volatility
from services.ta.indicators.volume import Volume
from services.ta.strategies.models.strategy import ComposeStrategiesListMethod, Strategy
from services.ta.strategies.operators import compose_strategies_list, get_stored_strategies
from utils.logger.operators import get_logger

log = get_logger()


def get_indicators(data, **kwargs) -> dict[str, dict[str, Indicator]]:  # type: ignore
    indicators_mapping = dict()

    trend = Trend(data)
    trend.add_trend_intensity_index(**SETTINGS.INDICATORS.get("Trend", {}).get("TII", {}))
    trend.add_average_directional_movement(**SETTINGS.INDICATORS.get("Trend", {}).get("ADX", {}))
    trend.add_parabolic_stop_and_reverse(**SETTINGS.INDICATORS.get("Trend", {}).get("PSAR", {}))
    trend.add_choppiness_index(**SETTINGS.INDICATORS.get("Trend", {}).get("CHOP", {}))

    overlap = Overlap(data)
    overlap.add_linear_regression(**SETTINGS.INDICATORS.get("Overlap", {}).get("LINREG", {}))
    overlap.add_slope(**SETTINGS.INDICATORS.get("Overlap", {}).get("SLOPE", {}))
    overlap.add_supertrend(**SETTINGS.INDICATORS.get("Overlap", {}).get("SUPERTREND", {}))

    momentum = Momentum(data)
    momentum.add_macd_dema(**SETTINGS.INDICATORS.get("Momentum", {}).get("MACD_DEMA", {}))
    momentum.add_schaff_trend_cycle(**SETTINGS.INDICATORS.get("Momentum", {}).get("STC", {}))
    momentum.add_commodity_channel_index(**SETTINGS.INDICATORS.get("Momentum", {}).get("CCI", {}))
    momentum.add_relative_vigor_index(**SETTINGS.INDICATORS.get("Momentum", {}).get("RVGI", {}))
    momentum.add_stochastic_oscillator(**SETTINGS.INDICATORS.get("Momentum", {}).get("STOCH", {}))

    cycles = Cycles(data)
    cycles.add_even_better_sinewave(**SETTINGS.INDICATORS.get("Cycles", {}).get("EBSW", {}))

    volatility = Volatility(data)
    volatility.add_starc_bands(**SETTINGS.INDICATORS.get("Volatility", {}).get("STARC", {}))
    volatility.add_mass_index(**SETTINGS.INDICATORS.get("Volatility", {}).get("MASSI", {}))
    volatility.add_bollinger_bands(**SETTINGS.INDICATORS.get("Volatility", {}).get("BBANDS", {}))
    volatility.add_acceleration_bands(**SETTINGS.INDICATORS.get("Volatility", {}).get("ACCBANDS", {}))

    volume = Volume(data)
    volume.add_price_volume_trend(**SETTINGS.INDICATORS.get("Volume", {}).get("PVT", {}))
    volume.add_accumulation_distribution_oscillator(**SETTINGS.INDICATORS.get("Volume", {}).get("ADOSC", {}))
    volume.add_chaikin_money_flow(**SETTINGS.INDICATORS.get("Volume", {}).get("CMF", {}))
    volume.add_klinger_volume_oscillator(**SETTINGS.INDICATORS.get("Volume", {}).get("KVO", {}))

    columns_keep = {"Open", "High", "Low", "Close", "Volume"}
    for category in [trend, volatility, volume, cycles, overlap, momentum]:
        for indicator in category.indicators.values():
            columns_keep |= set(indicator.columns)

        indicators_mapping[category.__class__.__name__] = category.indicators

    data.drop(columns=list(set(data.columns) - columns_keep), inplace=True)

    return indicators_mapping


def get_strategies(
    compose_strategies_list_method: ComposeStrategiesListMethod,
    indicators_mapping: dict[str, dict[str, Indicator]],
    strategies_file_name_prefix: str,
    strategies_file_name_suffix_old: str | None = None,
) -> list[Strategy]:
    return compose_strategies_list(
        compose_strategies_list_method,
        indicators_mapping,
        strategies_file_name_prefix,
        strategies_file_name_suffix_old,
    )


def read_top_strategies(
    indicators_mapping: dict[str, dict[str, Indicator]],
    strategies_file_name_prefix: str,
    filter_by_min_efficiency: float | None = None,
    limit_count: int | None = None,
) -> list[Strategy]:
    strategies = get_stored_strategies(indicators_mapping, strategies_file_name_prefix)

    if filter_by_min_efficiency:
        strategies = [strategy for strategy in strategies if strategy.efficiency >= filter_by_min_efficiency]

    if limit_count:
        strategies = strategies[:limit_count]

    strategies = sorted(strategies, key=lambda x: x.efficiency, reverse=True)

    return strategies
