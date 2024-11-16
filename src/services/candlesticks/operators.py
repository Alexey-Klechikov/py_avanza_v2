import warnings

import pandas as pd
import talib

from services.candlesticks.custom_patterns import CustomCandlestickPatterns
from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)
# Set display options
pd.set_option("display.max_rows", 100)  # Show up to 100 rows
pd.set_option("display.max_columns", 20)  # Show up to 20 columns
pd.set_option("display.width", 1000)  # Set the display width to 1000 characters
pd.set_option("display.max_colwidth", 100)  # Set the maximum column width to 100 characters
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
        smoothing=3,
        max_window_time_min=120,
    )
    custom_candlesticks_patterns.calculate_peaks()

    custom_candlesticks_patterns.append_head_and_shoulders(necklines_diff=0.0004)
    return data

    for i in range(len(data)):

        if i < 22:
            continue

        custom_candlesticks_patterns = CustomCandlestickPatterns(
            data=data.iloc[: i + 1],
            smoothing=4,
            max_window_time_min=120,
        )
        custom_candlesticks_patterns.calculate_peaks()

        custom_candlesticks_patterns.append_head_and_shoulders(necklines_diff=0.0004)
        # custom_candlesticks_patterns.append_double_top_bottom(peaks_diff=0.03)
        # custom_candlesticks_patterns.append_triangle(peaks_diff=0.03)
        if (
            len(
                custom_candlesticks_patterns.data[
                    custom_candlesticks_patterns.data["PTNHEADANDSHOULDERS"].isin([100, -100])
                ],
            )
            > 0
        ):
            print(custom_candlesticks_patterns.data.iloc[i])
            print(custom_candlesticks_patterns.data[["Close", "PTNHEADANDSHOULDERS"]].tail(100))

            raise

    return data
