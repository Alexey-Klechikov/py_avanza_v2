import pandas as pd

OHLCV_AGGREGATION = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}


def resample_ohlcv(history: pd.DataFrame, duration: pd.Timedelta) -> pd.DataFrame:
    """Bars of `duration` (bar-start labels) built from the finer `history`."""
    coarse_bars = history.resample(duration, label="left", closed="left").agg(OHLCV_AGGREGATION)

    return coarse_bars.dropna(subset=["Close"])


def completing_bars(history: pd.DataFrame, duration: pd.Timedelta, bar_duration: pd.Timedelta) -> pd.Series:
    """For each complete coarse bar (bar-start label), the `history` bar that completes it.

    `history` holds closed bars of `bar_duration` only. A coarse bar counts as complete once its last slot has
    closed or a later bar exists, so a coarse bar still in progress is left out.
    """
    bar_starts = pd.DatetimeIndex(history.index)
    if bar_starts.empty:
        return pd.Series(dtype="datetime64[ns]")

    last_bar_by_coarse_start = pd.Series(bar_starts, index=bar_starts).groupby(bar_starts.floor(duration)).last()
    coarse_ends = pd.DatetimeIndex(last_bar_by_coarse_start.index) + duration
    is_complete = (last_bar_by_coarse_start + bar_duration >= coarse_ends) | (
        last_bar_by_coarse_start < bar_starts[-1]
    )

    return last_bar_by_coarse_start[is_complete]
