import pandas as pd

from services.candlesticks.patterns.custom import append_custom_candlestick_patterns
from services.candlesticks.patterns.peak import append_peak_based_candlestick_patterns
from services.candlesticks.patterns.talib import append_talib_candlestick_patterns
from utils.logger.operators import get_logger

log = get_logger()


# MAIN
def append_candlestick_patterns(data: pd.DataFrame, candlestick_rules: list[str] | None = None) -> pd.DataFrame:
    data = append_talib_candlestick_patterns(data, candlestick_rules)
    data = append_custom_candlestick_patterns(data, candlestick_rules)
    data = append_peak_based_candlestick_patterns(data, candlestick_rules)

    return data
