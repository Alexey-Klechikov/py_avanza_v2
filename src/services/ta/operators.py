from collections.abc import Callable

import pandas as pd

from config import DATA_COLUMNS, SETTINGS
from services.ta.indicators.cycles import Cycles
from services.ta.indicators.models.category_base import IndicatorsCategoryBase
from services.ta.indicators.models.indicator import Indicator
from services.ta.indicators.momentum import Momentum
from services.ta.indicators.overlap import Overlap
from services.ta.indicators.trend import Trend
from services.ta.indicators.volatility import Volatility
from services.ta.indicators.volume import Volume

# Category order is the order of the returned mapping, so of the vote columns
CATEGORY_CLASSES: tuple[type[IndicatorsCategoryBase], ...] = (Trend, Volatility, Volume, Cycles, Overlap, Momentum)

INDICATOR_ADDERS: tuple[tuple[type[IndicatorsCategoryBase], str, Callable[..., None]], ...] = (
    (Trend, "TII", Trend.add_trend_intensity_index),
    (Trend, "ADX", Trend.add_average_directional_movement),
    (Trend, "PSAR", Trend.add_parabolic_stop_and_reverse),
    (Overlap, "LINREG", Overlap.add_linear_regression),
    (Overlap, "SLOPE", Overlap.add_slope),
    (Overlap, "SUPERTREND", Overlap.add_supertrend),
    (Momentum, "MACD_DEMA", Momentum.add_macd_dema),
    (Momentum, "STC", Momentum.add_schaff_trend_cycle),
    (Momentum, "RVGI", Momentum.add_relative_vigor_index),
    (Momentum, "STOCH", Momentum.add_stochastic_oscillator),
    (Momentum, "CCI", Momentum.add_commodity_channel_index),
    (Cycles, "EBSW", Cycles.add_even_better_sinewave),
    (Volatility, "STARC", Volatility.add_starc_bands),
    (Volatility, "BBANDS", Volatility.add_bollinger_bands),
    (Volatility, "ACCBANDS", Volatility.add_acceleration_bands),
    (Volume, "PVT", Volume.add_price_volume_trend),
    (Volume, "ADOSC", Volume.add_accumulation_distribution_oscillator),
    (Volume, "CMF", Volume.add_chaikin_money_flow),
    (Volume, "KVO", Volume.add_klinger_volume_oscillator),
)


def add_indicators(bars: pd.DataFrame) -> dict[str, dict[str, Indicator]]:
    """Add every indicator configured in SETTINGS.INDICATORS to `bars` (in place, dropping helper columns no
    indicator reads) and return them by category name."""
    categories = {category_class: category_class(bars) for category_class in CATEGORY_CLASSES}
    for category_class, indicator_name, add_indicator in INDICATOR_ADDERS:
        parameters = SETTINGS.INDICATORS.get(category_class.__name__, {}).get(indicator_name)
        if parameters:
            add_indicator(categories[category_class], **parameters)

    kept_columns = set(DATA_COLUMNS).union(
        *(indicator.columns for category in categories.values() for indicator in category.indicators.values()),
    )
    bars.drop(columns=[column for column in bars.columns if column not in kept_columns], inplace=True)

    return {category_class.__name__: category.indicators for category_class, category in categories.items()}
