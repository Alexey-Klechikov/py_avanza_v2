from collections.abc import Callable

import numpy as np
import pandas as pd

from config import SETTINGS
from services.ta.operators import add_indicators
from tasks.shared.bars import BAR_DURATION, bar_index
from tasks.shared.coarse_bars import completing_bars, resample_ohlcv

DAILY_PREFIX = "1d"


def _signal_flags(signal_method: Callable | None, bar_records: list[dict]) -> np.ndarray:
    if signal_method is None:
        return np.zeros(len(bar_records), dtype=np.int8)

    return np.fromiter((bool(signal_method(record)) for record in bar_records), dtype=np.int8, count=len(bar_records))


def _indicator_votes(bars: pd.DataFrame) -> pd.DataFrame:
    """Per bar of `bars`: "<indicator>:dir" (+1 LONG, -1 SHORT, 0)."""
    bars = bars.copy()
    indicators = [
        (f"{category}-{name}", indicator.signal)
        for category, category_indicators in add_indicators(bars).items()
        for name, indicator in category_indicators.items()
    ]
    bar_records = bars.to_dict("records")

    votes: dict[str, np.ndarray] = {}
    for name, signal in indicators:
        if signal.LONG or signal.SHORT:
            votes[f"{name}:dir"] = _signal_flags(signal.LONG, bar_records) - _signal_flags(signal.SHORT, bar_records)

    return pd.DataFrame(votes, index=bars.index)


def _intraday_votes(history: pd.DataFrame, resolution: str) -> pd.DataFrame:
    """Votes on `resolution` bars as known at each 2m bar: a coarse bar's votes hold from the 2m bar that
    completes it until the next coarse bar completes."""
    duration = pd.Timedelta(resolution)
    if duration == BAR_DURATION:
        return _indicator_votes(history).add_prefix(f"{resolution}:")

    completing_times = completing_bars(history, duration, BAR_DURATION)
    votes = _indicator_votes(resample_ohlcv(history, duration)).reindex(completing_times.index)
    votes.index = pd.DatetimeIndex(completing_times.to_numpy())

    return votes.reindex(history.index, method="ffill").add_prefix(f"{resolution}:")


def _daily_votes(index: pd.DatetimeIndex, daily: pd.DataFrame) -> pd.DataFrame:
    """Votes of the 1d bars, each known from the next calendar day on (a session uses the previous ones only)."""
    votes = _indicator_votes(daily)
    votes.index = bar_index(votes).normalize() + pd.Timedelta(days=1)

    session_days = index.normalize()
    by_day = votes.reindex(session_days.unique(), method="ffill")

    return by_day.reindex(session_days).set_axis(index).add_prefix(f"{DAILY_PREFIX}:")


def vote_frame(history: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Every vote (SETTINGS.WEIGHTED_SCORE) at each closed 2m bar of `history`; 0 where not known yet."""
    frames = [_intraday_votes(history, resolution) for resolution in SETTINGS.WEIGHTED_SCORE.RESOLUTIONS]
    if SETTINGS.WEIGHTED_SCORE.USE_DAILY:
        frames.append(_daily_votes(bar_index(history), daily))

    return pd.concat(frames, axis=1).fillna(0).astype(np.float32)
