import warnings

import pandas as pd
import talib

from services.candlesticks.custom_patterns import CustomCandlestickPatterns
from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

log = get_logger()


def append_talib_candlestick_patterns(data: pd.DataFrame, candlestick_rules: list[str] | None = None) -> pd.DataFrame:
    pattern_names = candlestick_rules or talib.get_function_groups()["Pattern Recognition"]

    for pattern_name in pattern_names:
        pattern_method = getattr(talib, pattern_name)
        pattern_column = pattern_method(data["Open"], data["High"], data["Low"], data["Close"])

        data[pattern_name] = pattern_column

    return data


def append_custom_candlestick_patterns(data: pd.DataFrame) -> pd.DataFrame:
    custom_candlesticks_patterns = CustomCandlestickPatterns(
        data=data,
        smoothing=2,
        max_window_time_min=120,
    )
    custom_candlesticks_patterns.calculate_peaks()

    custom_candlesticks_patterns.append_head_and_shoulders(necklines_diff=0.02)
    custom_candlesticks_patterns.append_double_top_bottom(peaks_diff=0.03)
    custom_candlesticks_patterns.append_triangle(peaks_diff=0.03)

    return data
