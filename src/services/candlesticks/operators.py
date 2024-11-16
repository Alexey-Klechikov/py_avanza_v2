import warnings

import pandas as pd
import talib

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
