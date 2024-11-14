"""
This code is forked from
https://github.com/keithorange/PatternPy/blob/main/tradingpatterns/tradingpatterns.py
"""

import numpy as np
import pandas as pd


# TODO: refactor - suspiciously good results
def append_triangle_pattern(data: pd.DataFrame, length: int = 3):
    column_name = f"PTNTRIANGLE_{length}"

    data["high_roll_max"] = data["High"].rolling(window=length).max()
    data["low_roll_min"] = data["Low"].rolling(window=length).min()

    mask_asc = (
        (data["high_roll_max"] >= data["High"].shift(1))
        & (data["low_roll_min"] <= data["Low"].shift(1))
        & (data["Close"] > data["Close"].shift(1))
    )
    mask_desc = (
        (data["high_roll_max"] <= data["High"].shift(1))
        & (data["low_roll_min"] >= data["Low"].shift(1))
        & (data["Close"] < data["Close"].shift(1))
    )

    data[column_name] = 0
    data.loc[mask_asc, column_name] = -100
    data.loc[mask_desc, column_name] = 100

    data.drop(["high_roll_max", "low_roll_min"], axis=1, inplace=True)

    return data


def append_wedge(data: pd.DataFrame, length: int = 3):
    column_name = f"PTNWEDGE_{length}"

    data["high_roll_max"] = data["High"].rolling(window=length).max()
    data["low_roll_min"] = data["Low"].rolling(window=length).min()
    data["trend_high"] = (
        data["High"].rolling(window=length).apply(lambda x: 1 if (x[-1] - x[0]) > 0 else -1 if (x[-1] - x[0]) < 0 else 0)
    )
    data["trend_low"] = (
        data["Low"].rolling(window=length).apply(lambda x: 1 if (x[-1] - x[0]) > 0 else -1 if (x[-1] - x[0]) < 0 else 0)
    )

    mask_wedge_up = (
        (data["high_roll_max"] >= data["High"].shift(1))
        & (data["low_roll_min"] <= data["Low"].shift(1))
        & (data["trend_high"] == 1)
        & (data["trend_low"] == 1)
    )
    mask_wedge_down = (
        (data["high_roll_max"] <= data["High"].shift(1))
        & (data["low_roll_min"] >= data["Low"].shift(1))
        & (data["trend_high"] == -1)
        & (data["trend_low"] == -1)
    )

    data[column_name] = 0
    data.loc[mask_wedge_up, column_name] = -100
    data.loc[mask_wedge_down, column_name] = 100

    data.drop(["high_roll_max", "low_roll_min", "trend_high", "trend_low"], axis=1, inplace=True)

    return data


def append_channel(data: pd.DataFrame, length: int = 3, channel_range: float = 0.1):
    column_name = f"PTNCHANNEL_{length}"

    data["high_roll_max"] = data["High"].rolling(window=length).max()
    data["low_roll_min"] = data["Low"].rolling(window=length).min()
    data["trend_high"] = (
        data["High"].rolling(window=length).apply(lambda x: 1 if (x[-1] - x[0]) > 0 else -1 if (x[-1] - x[0]) < 0 else 0)
    )
    data["trend_low"] = (
        data["Low"].rolling(window=length).apply(lambda x: 1 if (x[-1] - x[0]) > 0 else -1 if (x[-1] - x[0]) < 0 else 0)
    )

    mask_channel_up = (
        (data["high_roll_max"] >= data["High"].shift(1))
        & (data["low_roll_min"] <= data["Low"].shift(1))
        & (
            data["high_roll_max"] - data["low_roll_min"]
            <= channel_range * (data["high_roll_max"] + data["low_roll_min"]) / 2
        )
        & (data["trend_high"] == 1)
        & (data["trend_low"] == 1)
    )
    mask_channel_down = (
        (data["high_roll_max"] <= data["High"].shift(1))
        & (data["low_roll_min"] >= data["Low"].shift(1))
        & (
            data["high_roll_max"] - data["low_roll_min"]
            <= channel_range * (data["high_roll_max"] + data["low_roll_min"]) / 2
        )
        & (data["trend_high"] == -1)
        & (data["trend_low"] == -1)
    )

    data[column_name] = 0
    data.loc[mask_channel_up, column_name] = -100
    data.loc[mask_channel_down, column_name] = 100

    data.drop(["high_roll_max", "low_roll_min", "trend_high", "trend_low"], axis=1, inplace=True)

    return data


# TODO: refactor - it looks into the future
def append_head_and_shoulders(data: pd.DataFrame, length: int = 3):
    column_name = f"PTNHEADANDSHOULDERS_{length}"

    data["high_roll_max"] = data["High"].rolling(window=length).max()
    data["low_roll_min"] = data["Low"].rolling(window=length).min()

    mask_head_shoulder = (
        (data["high_roll_max"] > data["High"].shift(1))
        & (data["high_roll_max"] > data["High"].shift(-1))
        & (data["High"] < data["High"].shift(1))
        & (data["High"] < data["High"].shift(-1))
    )
    mask_inv_head_shoulder = (
        (data["low_roll_min"] < data["Low"].shift(1))
        & (data["low_roll_min"] < data["Low"].shift(-1))
        & (data["Low"] > data["Low"].shift(1))
        & (data["Low"] > data["Low"].shift(-1))
    )

    data[column_name] = 0
    data.loc[mask_head_shoulder, column_name] = 100
    data.loc[mask_inv_head_shoulder, column_name] = -100

    data.drop(["high_roll_max", "low_roll_min"], axis=1, inplace=True)

    return data


def append_double_top_bottom(data: pd.DataFrame, length: int = 3, threshold: float = 0.05):
    column_name = f"PTNDOUBLETOPBOTTOM_{length}"

    data["high_roll_max"] = data["High"].rolling(window=length).max()
    data["low_roll_min"] = data["Low"].rolling(window=length).min()

    mask_double_top = (
        (data["high_roll_max"] >= data["High"].shift(1))
        & (data["high_roll_max"] >= data["High"].shift(-1))
        & (data["High"] < data["High"].shift(1))
        & (data["High"] < data["High"].shift(-1))
        & (
            (data["High"].shift(1) - data["Low"].shift(1))
            <= threshold * (data["High"].shift(1) + data["Low"].shift(1)) / 2
        )
        & (
            (data["High"].shift(-1) - data["Low"].shift(-1))
            <= threshold * (data["High"].shift(-1) + data["Low"].shift(-1)) / 2
        )
    )
    mask_double_bottom = (
        (data["low_roll_min"] <= data["Low"].shift(1))
        & (data["low_roll_min"] <= data["Low"].shift(-1))
        & (data["Low"] > data["Low"].shift(1))
        & (data["Low"] > data["Low"].shift(-1))
        & (
            (data["High"].shift(1) - data["Low"].shift(1))
            <= threshold * (data["High"].shift(1) + data["Low"].shift(1)) / 2
        )
        & (
            (data["High"].shift(-1) - data["Low"].shift(-1))
            <= threshold * (data["High"].shift(-1) + data["Low"].shift(-1)) / 2
        )
    )

    data[column_name] = 0
    data.loc[mask_double_top, column_name] = 100
    data.loc[mask_double_bottom, column_name] = -100

    data.drop(["high_roll_max", "low_roll_min"], axis=1, inplace=True)

    return data


# TODO: research this
def append_calculate_support_resistance(data: pd.DataFrame, length: int = 3, std_dev: int = 2):
    column_name = f"PTNSUPPORTRESISTANCE_{length}"

    data["high_roll_max"] = data["High"].rolling(window=length).max()
    data["low_roll_min"] = data["Low"].rolling(window=length).min()

    mean_high = data["High"].rolling(window=length).mean()
    std_high = data["High"].rolling(window=length).std()
    mean_low = data["Low"].rolling(window=length).mean()
    std_low = data["Low"].rolling(window=length).std()

    data[f"{column_name}_support"] = mean_low - std_dev * std_low
    data[f"{column_name}_resistance"] = mean_high + std_dev * std_high

    data.drop(["high_roll_max", "low_roll_min"], axis=1, inplace=True)

    print(data)

    return data


def append_trendline(data, window=2):
    column_name = "PTNTRENDLINE"

    data["slope"] = np.nan
    data["intercept"] = np.nan

    for i in range(window, len(data)):
        x = np.array(range(i - window, i))
        y = data["Close"][i - window : i]
        A = np.vstack([x, np.ones(len(x))]).T
        m, c = np.linalg.lstsq(A, y, rcond=None)[0]
        data.at[data.index[i], "slope"] = m
        data.at[data.index[i], "intercept"] = c

    mask_support = data["slope"] > 0
    mask_resistance = data["slope"] < 0

    data[f"{column_name}_support"] = 0
    data[f"{column_name}_resistance"] = 0

    data.loc[mask_support, "support"] = data["Close"] * data["slope"] + data["intercept"]
    data.loc[mask_resistance, "resistance"] = data["Close"] * data["slope"] + data["intercept"]

    data.drop(["slope", "intercept"], axis=1, inplace=True)

    return data


def find_pivots(data):
    column_name = "PTNPIVOTS"

    high_diffs = data["high"].diff()
    low_diffs = data["low"].diff()

    higher_high_mask = (high_diffs > 0) & (high_diffs.shift(-1) < 0)
    lower_low_mask = (low_diffs < 0) & (low_diffs.shift(-1) > 0)
    lower_high_mask = (high_diffs < 0) & (high_diffs.shift(-1) > 0)
    higher_low_mask = (low_diffs > 0) & (low_diffs.shift(-1) < 0)

    data[column_name] = ""
    data.loc[higher_high_mask, column_name] = "HH"
    data.loc[lower_low_mask, column_name] = "LL"
    data.loc[lower_high_mask, column_name] = "LH"
    data.loc[higher_low_mask, column_name] = "HL"

    return data
