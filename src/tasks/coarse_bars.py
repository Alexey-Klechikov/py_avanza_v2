import pandas as pd

from config import SETTINGS
from tasks.backtest.bars import bar_index

BAR_DURATION = pd.Timedelta(SETTINGS.RESOLUTION)
OHLCV_AGGREGATION = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}


def resample_ohlcv(history: pd.DataFrame, duration: pd.Timedelta) -> pd.DataFrame:
    """Bars of `duration` (bar-start labels) built from the 2m `history`."""
    coarse = history.resample(duration, label="left", closed="left").agg(OHLCV_AGGREGATION)

    return coarse.dropna(subset=["Close"])


def completing_bars(history: pd.DataFrame, duration: pd.Timedelta) -> pd.Series:
    """For each complete coarse bar (bar-start label), the 2m bar that completes it.

    `history` holds closed 2m bars only. A coarse bar counts as complete once its last 2m slot has closed or a later
    bar exists, so a coarse bar still in progress is left out.
    """
    times = bar_index(history)
    by_bucket = pd.Series(times, index=times).groupby(times.floor(duration)).last()
    is_complete = (by_bucket + BAR_DURATION >= bar_index(by_bucket) + duration) | (by_bucket < times[-1])

    return by_bucket[is_complete]
