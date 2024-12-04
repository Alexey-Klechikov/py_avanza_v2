import pandas as pd

from utils.logger import get_logger

log = get_logger()


# Candlesticks based
def hook_reversal(data: pd.DataFrame) -> list[int]:
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
            signal = 100

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
            signal = -100

        pattern_column.append(signal)

    return pattern_column


def three_gaps(data: pd.DataFrame) -> list[int]:
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


def kicker(data: pd.DataFrame) -> list[int]:
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
            signal = 100

        elif (
            window.iloc[0]["Close"] > window.iloc[0]["Open"]  # green
            and window.iloc[1]["Close"] < window.iloc[1]["Open"]  # red
            and window.iloc[0]["Open"] > window.iloc[1]["Open"]  # gap down
            and (window.iloc[1]["Open"] - window.iloc[1]["Close"]) / (window.iloc[0]["Close"] - window.iloc[0]["Open"])
            > 2  # red is at least 2x bigger than green
        ):
            signal = -100

        pattern_column.append(signal)

    return pattern_column


def tweezer(data: pd.DataFrame) -> list[int]:
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


def engulfing_three(data: pd.DataFrame) -> list[int]:
    pattern_column = []
    for i in range(len(data)):
        if i < 3:
            pattern_column.append(0)
            continue

        window = data.iloc[i - 2 : i + 1]

        signal = 0
        if (
            window.iloc[0]["Close"] < window.iloc[0]["Open"]  # red
            and window.iloc[1]["Close"] < window.iloc[1]["Open"]  # red
            and window.iloc[2]["Close"] > window.iloc[2]["Open"]  # green
            and window.iloc[2]["High"] >= window["High"].max()  # green is engulfing all previous
            and window.iloc[2]["Low"] <= window["Low"].min()  # green is engulfing all previous
        ):
            signal = -100

        elif (
            window.iloc[0]["Close"] > window.iloc[0]["Open"]  # green
            and window.iloc[1]["Close"] > window.iloc[1]["Open"]  # green
            and window.iloc[2]["Close"] < window.iloc[2]["Open"]  # red
            and window.iloc[2]["High"] >= window["High"].max()  # green is engulfing all previous
            and window.iloc[2]["Low"] <= window["Low"].max()  # green is engulfing all previous
        ):
            signal = 100

        pattern_column.append(signal)

    return pattern_column


# MAIN
def append_custom_candlestick_patterns(data: pd.DataFrame, candlestick_rules: list[str] | None = None) -> pd.DataFrame:
    for pattern_name, method in [
        ("CDL_CUSTOM_HOOKREVERSAL", hook_reversal),
        ("CDL_CUSTOM_THREEGAPS", three_gaps),
        ("CDL_CUSTOM_KICKER", kicker),
        ("CDL_CUSTOM_TWEEZER", tweezer),
        ("CDL_CUSTOM_ENGULFINGTHREE", engulfing_three),
    ]:
        if candlestick_rules and pattern_name not in candlestick_rules:
            continue

        data[pattern_name] = method(data)

    return data
