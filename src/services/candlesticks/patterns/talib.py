import pandas as pd
import talib

from utils.logger.operators import get_logger

log = get_logger()


def append_talib_candlestick_patterns(data: pd.DataFrame, candlestick_rules: list[str] | None = None) -> pd.DataFrame:
    for pattern_name in talib.get_function_groups()["Pattern Recognition"]:
        if candlestick_rules and pattern_name.replace("CDL", "CDL_TALIB_") not in candlestick_rules:
            continue

        pattern_method = getattr(talib, pattern_name)
        pattern_column = pattern_method(data["Open"], data["High"], data["Low"], data["Close"])

        data[pattern_name.replace("CDL", "CDL_TALIB_")] = pattern_column

    return data
