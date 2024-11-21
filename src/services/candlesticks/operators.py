import pandas as pd

from services.candlesticks.patterns import (
    append_custom_candlestick_patterns,
    append_peak_based_candlestick_patterns,
    append_talib_candlestick_patterns,
)
from utils.logger import get_logger

log = get_logger()


# MAIN
def append_candlestick_patterns(data: pd.DataFrame, candlestick_rules: list[str] | None = None) -> pd.DataFrame:
    data = append_talib_candlestick_patterns(data, candlestick_rules)
    data = append_custom_candlestick_patterns(data, candlestick_rules)
    data = append_peak_based_candlestick_patterns(data, candlestick_rules)

    return data
