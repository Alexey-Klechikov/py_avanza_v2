import numpy as np
import pandas as pd
from scipy.signal import argrelextrema

from utils.logger import get_logger

log = get_logger()


def _calculate_peaks(data: pd.DataFrame, window_smoothing: int, window_peak: int) -> pd.DataFrame:
    data["Peak"] = 0

    smoothed_data = data["Close"].rolling(window=window_smoothing).mean()
    smoothed_data.iloc[-1] = data["Close"].iloc[-1]

    local_max_indexes = []
    for smoothed_data_index in argrelextrema(smoothed_data.values, np.greater, order=window_peak)[0]:
        data_at_window_smoothing = data.iloc[smoothed_data_index - window_smoothing + 1 : smoothed_data_index + 1]
        local_max_indexes.append(data_at_window_smoothing["Close"].idxmax())
    data.loc[local_max_indexes, "Peak"] = 1

    local_min_indexes = []
    for smoothed_data_index in argrelextrema(smoothed_data.values, np.less, order=window_peak)[0]:
        data_at_window_smoothing = data.iloc[smoothed_data_index - window_smoothing + 1 : smoothed_data_index + 1]
        local_min_indexes.append(data_at_window_smoothing["Close"].idxmin())
    data.loc[local_min_indexes, "Peak"] = -1

    return data


def _same_peaks(window: pd.DataFrame, peaks_indexes: tuple[int, int], same_peak_threshold: float = 0.0003) -> bool:
    first_peak = window.iloc[peaks_indexes[0]]["Close"]
    second_peak = window.iloc[peaks_indexes[1]]["Close"]

    return abs(first_peak - second_peak) / first_peak < same_peak_threshold


def head_and_shoulders(data: pd.DataFrame, window_duration_min: int = 75) -> list[int]:
    data_filtered = data[data["Peak"] != 0][["Close", "Peak"]].copy()
    data["_signal"] = 0

    for i in range(len(data_filtered)):
        if i < 4:
            continue

        window = data_filtered.iloc[i - 4 : i + 1]

        if (window.iloc[-1].name - window.iloc[0].name).seconds >= window_duration_min * 60:  # type: ignore
            continue

        signal = 0

        if (
            window.iloc[0]["Peak"] == 1  # (1) first top
            and window.iloc[1]["Peak"] == -1  # (2) first bottom
            and window.iloc[2]["Peak"] == 1  # (3) second top
            and window.iloc[3]["Peak"] == -1  # (4) second bottom
            and window.iloc[4]["Peak"] == 1  # (5) third top
            and _same_peaks(window, (1, 3))  # (2) == (4)
            and _same_peaks(window, (0, 4))  # (1) == (5)
            and window.iloc[2]["Close"] > window.iloc[0]["Close"]  # (3) > (1)
        ):
            signal = -100

        elif (
            window.iloc[0]["Peak"] == -1  # (1) first bottom
            and window.iloc[1]["Peak"] == 1  # (2) first top
            and window.iloc[2]["Peak"] == -1  # (3) second bottom
            and window.iloc[3]["Peak"] == 1  # (4) second top
            and window.iloc[4]["Peak"] == -1  # (5) third bottom
            and _same_peaks(window, (0, 4))  # (1) == (5)
            and _same_peaks(window, (1, 3))  # (2) == (4)
            and window.iloc[2]["Close"] < window.iloc[0]["Close"]  # (3) < (1)
        ):
            signal = 100

        if signal:
            signal_time_with_shift = window.iloc[-1].name + pd.Timedelta(minutes=4)  # type: ignore
            data.loc[signal_time_with_shift, "_signal"] = signal  # type: ignore

    pattern_column = data["_signal"].values.tolist()
    data.drop(columns=["_signal"], inplace=True)

    return pattern_column


def triangle(data: pd.DataFrame, window_duration_min: int = 75) -> list[int]:
    # This pattern is reversed compared to the one in the .png file

    data_filtered = data[data["Peak"] != 0][["Close", "Peak"]].copy()
    data["_signal"] = 0

    for i in range(len(data_filtered)):
        if i < 4:
            continue

        window = data_filtered.iloc[i - 4 : i + 1]

        if (window.iloc[-1].name - window.iloc[0].name).seconds >= window_duration_min * 60:  # type: ignore
            continue

        signal = 0

        if (
            window.iloc[0]["Peak"] == 1  # (1) first top
            and window.iloc[1]["Peak"] == -1  # (2) first bottom
            and window.iloc[2]["Peak"] == 1  # (3) second top
            and window.iloc[3]["Peak"] == -1  # (4) second bottom
            and window.iloc[4]["Peak"] == 1  # (5) third top
            and round(window.iloc[3]["Close"], 1) >= round(window.iloc[1]["Close"], 1)  # (4) >= (2)
            and round(window.iloc[4]["Close"], 1) >= round(window.iloc[2]["Close"], 1)  # (5) >= (3)
            and round(window.iloc[0]["Close"], 1) >= round(window.iloc[2]["Close"], 1)  # (1) >= (3)
        ):
            signal = -100

        elif (
            window.iloc[0]["Peak"] == -1  # (1) first bottom
            and window.iloc[1]["Peak"] == 1  # (2) first top
            and window.iloc[2]["Peak"] == -1  # (3) second bottom
            and window.iloc[3]["Peak"] == 1  # (4) second top
            and window.iloc[4]["Peak"] == -1  # (5) third bottom
            and round(window.iloc[3]["Close"], 1) <= round(window.iloc[1]["Close"], 1)  # (4) <= (2)
            and round(window.iloc[4]["Close"], 1) <= round(window.iloc[2]["Close"], 1)  # (5) <= (3)
            and round(window.iloc[0]["Close"], 1) <= round(window.iloc[2]["Close"], 1)  # (1) <= (3)
        ):
            signal = 100

        if signal:
            signal_time_with_shift = window.iloc[-1].name + pd.Timedelta(minutes=4)  # type: ignore
            data.loc[signal_time_with_shift, "_signal"] = signal  # type: ignore

    pattern_column = data["_signal"].values.tolist()
    data.drop(columns=["_signal"], inplace=True)

    return pattern_column


def double_peak(data: pd.DataFrame, window_duration_min: int = 75) -> list[int]:
    data_filtered = data[data["Peak"] != 0][["Close", "Peak"]].copy()
    data["_signal"] = 0

    for i in range(len(data_filtered)):
        if i < 3:
            continue

        window = data_filtered.iloc[i - 3 : i + 1]

        if (window.iloc[-1].name - window.iloc[0].name).seconds >= window_duration_min * 60:  # type: ignore
            continue

        signal = 0

        if (
            window.iloc[0]["Peak"] == 1  # (1) first top
            and window.iloc[1]["Peak"] == -1  # (2) first bottom
            and window.iloc[2]["Peak"] == 1  # (3) second top
            and window.iloc[3]["Peak"] == -1  # (4) second bottom
            and _same_peaks(window, (0, 2))  # (1) == (3)
            and round(window.iloc[3]["Close"], 1) < round(window.iloc[1]["Close"], 1)  # (4) < (2)
        ):
            signal = 100

        elif (
            window.iloc[0]["Peak"] == -1  # (1) first bottom
            and window.iloc[1]["Peak"] == 1  # (2) first top
            and window.iloc[2]["Peak"] == -1  # (3) second bottom
            and window.iloc[3]["Peak"] == 1  # (4) second top
            and _same_peaks(window, (0, 2))  # (1) == (3)
            and round(window.iloc[3]["Close"], 1) > round(window.iloc[1]["Close"], 1)  # (4) > (2)
        ):
            signal = -100

        if signal:
            signal_time_with_shift = window.iloc[-1].name + pd.Timedelta(minutes=4)  # type: ignore
            data.loc[signal_time_with_shift, "_signal"] = signal  # type: ignore

    pattern_column = data["_signal"].values.tolist()
    data.drop(columns=["_signal"], inplace=True)

    return pattern_column


def triple_peak(data: pd.DataFrame, window_duration_min: int = 75) -> list[int]:
    data_filtered = data[data["Peak"] != 0][["Close", "Peak"]].copy()
    data["_signal"] = 0

    for i in range(len(data_filtered)):
        if i < 5:
            continue

        window = data_filtered.iloc[i - 5 : i + 1]

        if (window.iloc[-1].name - window.iloc[0].name).seconds >= window_duration_min * 60:  # type: ignore
            continue

        signal = 0

        if (
            window.iloc[0]["Peak"] == 1  # (1) first top
            and window.iloc[1]["Peak"] == -1  # (2) first bottom
            and window.iloc[2]["Peak"] == 1  # (3) second top
            and window.iloc[3]["Peak"] == -1  # (4) second bottom
            and window.iloc[4]["Peak"] == 1  # (5) first top
            and window.iloc[5]["Peak"] == -1  # (6) first bottom
            and _same_peaks(window, (0, 2))  # (1) == (3)
            and _same_peaks(window, (2, 4))  # (3) == (5)
            and round(window.iloc[5]["Close"], 1)
            < min([round(window.iloc[1]["Close"], 1), round(window.iloc[3]["Close"], 1)])  # (6) < min[(2), (4)]
        ):
            signal = 100

        elif (
            window.iloc[0]["Peak"] == -1  # (1) first bottom
            and window.iloc[1]["Peak"] == 1  # (2) first top
            and window.iloc[2]["Peak"] == -1  # (3) second bottom
            and window.iloc[3]["Peak"] == 1  # (4) second top
            and window.iloc[4]["Peak"] == -1  # (5) first bottom
            and window.iloc[5]["Peak"] == 1  # (6) first top
            and _same_peaks(window, (0, 2))  # (1) == (3)
            and _same_peaks(window, (2, 4))  # (3) == (5)
            and round(window.iloc[5]["Close"], 1)
            > min([round(window.iloc[1]["Close"], 1), max(window.iloc[3]["Close"], 1)])  # (6) > max[(2), (4)]
        ):
            signal = -100

        if signal:
            signal_time_with_shift = window.iloc[-1].name + pd.Timedelta(minutes=4)  # type: ignore
            data.loc[signal_time_with_shift, "_signal"] = signal  # type: ignore

    pattern_column = data["_signal"].values.tolist()
    data.drop(columns=["_signal"], inplace=True)

    return pattern_column


# MAIN
def append_peak_based_candlestick_patterns(
    data: pd.DataFrame,
    candlestick_rules: list[str] | None = None,
) -> pd.DataFrame:
    data = _calculate_peaks(data, window_smoothing=5, window_peak=3)

    for pattern_name, method in [
        ("CDL_PEAK_HEADANDSHOULDERS", head_and_shoulders),
        ("CDL_PEAK_TRIANGLE", triangle),
        ("CDL_PEAK_DOUBLEPEAK", double_peak),
        ("CDL_PEAK_TRIPLEPEAK", triple_peak),
    ]:
        if candlestick_rules and pattern_name not in candlestick_rules:
            continue

        data[pattern_name] = method(data)

    return data
