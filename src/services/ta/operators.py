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


def get_indicators(data, **_) -> dict[str, dict[str, Indicator]]:
    indicators_mapping = dict()

    trend = Trend(data)
    settings_trend = SETTINGS.INDICATORS.get("Trend", {})
    if settings_trend.get("TII"):
        trend.add_trend_intensity_index(**settings_trend["TII"])
    if settings_trend.get("ADX"):
        trend.add_average_directional_movement(**settings_trend["ADX"])
    if settings_trend.get("PSAR"):
        trend.add_parabolic_stop_and_reverse(**settings_trend["PSAR"])
    if settings_trend.get("CHOP"):
        trend.add_choppiness_index(**settings_trend["CHOP"])

    overlap = Overlap(data)
    settings_overlap = SETTINGS.INDICATORS.get("Overlap", {})
    if settings_overlap.get("LINREG"):
        overlap.add_linear_regression(**settings_overlap["LINREG"])
    if settings_overlap.get("SLOPE"):
        overlap.add_slope(**settings_overlap["SLOPE"])
    if settings_overlap.get("SUPERTREND"):
        overlap.add_supertrend(**settings_overlap["SUPERTREND"])

    momentum = Momentum(data)
    settings_momentum = SETTINGS.INDICATORS.get("Momentum", {})
    if settings_momentum.get("MACD_DEMA"):
        momentum.add_macd_dema(**settings_momentum["MACD_DEMA"])
    if settings_momentum.get("STC"):
        momentum.add_schaff_trend_cycle(**settings_momentum["STC"])
    if settings_momentum.get("RVGI"):
        momentum.add_relative_vigor_index(**settings_momentum["RVGI"])
    if settings_momentum.get("STOCH"):
        momentum.add_stochastic_oscillator(**settings_momentum["STOCH"])
    if settings_momentum.get("CCI"):
        momentum.add_commodity_channel_index(**settings_momentum["CCI"])

    cycles = Cycles(data)
    settings_cycles = SETTINGS.INDICATORS.get("Cycles", {})
    if settings_cycles.get("EBSW"):
        cycles.add_even_better_sinewave(**settings_cycles["EBSW"])

    volatility = Volatility(data)
    settings_volatility = SETTINGS.INDICATORS.get("Volatility", {})
    if settings_volatility.get("STARC"):
        volatility.add_starc_bands(**settings_volatility["STARC"])
    if settings_volatility.get("MASSI"):
        volatility.add_mass_index(**settings_volatility["MASSI"])
    if settings_volatility.get("BBANDS"):
        volatility.add_bollinger_bands(**settings_volatility["BBANDS"])
    if settings_volatility.get("ACCBANDS"):
        volatility.add_acceleration_bands(**settings_volatility["ACCBANDS"])

    volume = Volume(data)
    settings_volume = SETTINGS.INDICATORS.get("Volume", {})
    if settings_volume.get("PVT"):
        volume.add_price_volume_trend(**settings_volume["PVT"])
    if settings_volume.get("ADOSC"):
        volume.add_accumulation_distribution_oscillator(**settings_volume["ADOSC"])
    if settings_volume.get("CMF"):
        volume.add_chaikin_money_flow(**settings_volume["CMF"])
    if settings_volume.get("KVO"):
        volume.add_klinger_volume_oscillator(**settings_volume["KVO"])

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
