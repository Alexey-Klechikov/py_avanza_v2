import warnings

import pandas as pd
import talib

from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

log = get_logger()


def _hook_reversal(data):
    pattern_column = []
    for i in range(len(data)):
        if i < 3:
            pattern_column.append(0)
            continue

        window = data.iloc[i - 3 : i + 1]

        signal = 0
        if (
            window.iloc[0]["Close"] > window.iloc[0]["Open"]  # green
            and window.iloc[1]["Close"] > window.iloc[1]["Open"]  # green
            and window.iloc[2]["Close"] < window.iloc[2]["Open"]  # red
            and window.iloc[3]["Close"] < window.iloc[3]["Open"]  # red
            and window.iloc[1]["Low"] < window.iloc[2]["Low"]  # first middle low is lower than second middle low
            and window.iloc[1]["Low"]
            <= window.iloc[2]["Close"]
            <= window.iloc[2]["Open"]
            <= window.iloc[1]["High"]  # first red is inside last green
        ):
            signal = -100

        elif (
            window.iloc[0]["Close"] < window.iloc[0]["Open"]  # red
            and window.iloc[1]["Close"] < window.iloc[1]["Open"]  # red
            and window.iloc[2]["Close"] > window.iloc[2]["Open"]  # green
            and window.iloc[3]["Close"] > window.iloc[3]["Open"]  # green
            and window.iloc[1]["High"] > window.iloc[2]["High"]  # first middle high is higher than second middle high
            and window.iloc[1]["Low"]
            <= window.iloc[2]["Close"]
            <= window.iloc[2]["Open"]
            <= window.iloc[1]["High"]  # first green is inside last red
        ):
            signal = 100

        pattern_column.append(signal)

    return pattern_column


def _three_gaps(data):
    pattern_column = []
    for i in range(len(data)):
        if i < 2:
            pattern_column.append(0)
            continue

        window = data.iloc[i - 2 : i + 1]

        signal = 0
        if (
            window.iloc[0]["Close"] > window.iloc[0]["Open"]  # green
            and window.iloc[1]["Close"] > window.iloc[1]["Open"]  # green
            and window.iloc[2]["Close"] < window.iloc[2]["Open"]  # green
            and window.iloc[0]["Close"] < window.iloc[1]["Open"]  # gap 1
            and window.iloc[1]["Close"] < window.iloc[2]["Open"]  # gap 2
        ):
            signal = -100

        elif (
            window.iloc[0]["Close"] < window.iloc[0]["Open"]  # red
            and window.iloc[1]["Close"] < window.iloc[1]["Open"]  # red
            and window.iloc[2]["Close"] < window.iloc[2]["Open"]  # red
            and window.iloc[0]["Close"] > window.iloc[1]["Open"]  # gap 1
            and window.iloc[1]["Close"] > window.iloc[2]["Open"]  # gap 2
        ):
            signal = 100

        pattern_column.append(signal)

    return pattern_column


def _kicker(data):
    pattern_column = []
    for i in range(len(data)):
        if i < 1:
            pattern_column.append(0)
            continue

        window = data.iloc[i - 1 : i + 1]

        signal = 0
        if (
            window.iloc[0]["Close"] < window.iloc[0]["Open"]  # red
            and window.iloc[1]["Close"] > window.iloc[1]["Open"]  # green
            and window.iloc[0]["Open"] < window.iloc[1]["Open"]  # gap up
            and (window.iloc[1]["Close"] - window.iloc[1]["Open"]) / (window.iloc[0]["Open"] - window.iloc[0]["Close"])
            > 2  # green is at least 2x bigger than red
        ):
            signal = -100

        elif (
            window.iloc[0]["Close"] > window.iloc[0]["Open"]  # green
            and window.iloc[1]["Close"] < window.iloc[1]["Open"]  # red
            and window.iloc[0]["Open"] > window.iloc[1]["Open"]  # gap down
            and (window.iloc[1]["Open"] - window.iloc[1]["Close"]) / (window.iloc[0]["Close"] - window.iloc[0]["Open"])
            > 2  # red is at least 2x bigger than green
        ):
            signal = 100

        pattern_column.append(signal)

    return pattern_column


def _tweezer(data):
    pattern_column = []
    for i in range(len(data)):
        if i < 3:
            pattern_column.append(0)
            continue

        window = data.iloc[i - 2 : i + 1]

        signal = 0
        if (
            window.iloc[0]["Close"] < window.iloc[0]["Open"]  # red
            and window.iloc[1]["Close"] > window.iloc[1]["Open"]  # green
            and window.iloc[2]["Close"] > window.iloc[2]["Open"]  # green
            and window.iloc[0]["Low"] == window.iloc[1]["Low"]  # same lows
        ):
            signal = 100

        elif (
            window.iloc[0]["Close"] > window.iloc[0]["Open"]  # green
            and window.iloc[1]["Close"] < window.iloc[1]["Open"]  # red
            and window.iloc[2]["Close"] < window.iloc[2]["Open"]  # red
            and window.iloc[0]["High"] == window.iloc[1]["High"]  # same highs
        ):
            signal = -100

        pattern_column.append(signal)

    return pattern_column


# MAIN
def append_talib_candlestick_patterns(data: pd.DataFrame, candlestick_rules: list[str] | None = None) -> pd.DataFrame:
    pattern_names = candlestick_rules or talib.get_function_groups()["Pattern Recognition"]

    for pattern_name in pattern_names:
        pattern_method = getattr(talib, pattern_name)
        pattern_column = pattern_method(data["Open"], data["High"], data["Low"], data["Close"])

        data[pattern_name] = pattern_column

    return data


def append_custom_candlestick_patterns(data: pd.DataFrame) -> pd.DataFrame:
    data["CDLHOOKREVERSAL"] = _hook_reversal(data)
    data["CDLTHREEGAPS"] = _three_gaps(data)
    data["CDLKICKER"] = _kicker(data)
    data["CDLTWEEZER"] = _tweezer(data)

    return data
