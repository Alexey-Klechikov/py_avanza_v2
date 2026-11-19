from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import date
from typing import NamedTuple

import numpy as np
import pandas as pd
from pydantic import BaseModel

from config import SETTINGS
from tasks.backtest.paper_trade import PaperSession, replay
from tasks.shared.bars import add_execution_columns, bar_index, is_in_trading_window
from tasks.shared.votes import vote_frame
from tasks.shared.weighted_model import WEIGHTED_LEVELS, fit_model, forward_move_bp, weighted_signal_bars
from utils.logger.operators import get_logger

log = get_logger()


class WeightedWalkForward(BaseModel):
    """Out-of-sample result of refitting the weighted score every `refit_sessions` sessions on the data before."""

    sessions: dict[date, PaperSession]
    # Per refit period: correlation of the score with the HORIZON_BARS move it predicts, and votes kept
    correlations: list[float]
    kept_votes: list[int]


@dataclass(frozen=True)
class _WalkForwardFrames:
    """Everything a refit period reads; built once per walk-forward and shared by every period."""

    history: pd.DataFrame
    votes: pd.DataFrame
    bars: pd.DataFrame
    target: np.ndarray
    bar_days: np.ndarray
    is_scorable: np.ndarray
    warmed_up_start: pd.Timestamp


class _PeriodResult(NamedTuple):
    signal_bars: pd.DataFrame
    correlation: float
    kept_votes: int


# A worker process receives the frames once through the pool initializer, not once per period (votes alone are
# tens of MB)
_worker_frames: _WalkForwardFrames | None = None


def _set_worker_frames(frames: _WalkForwardFrames) -> None:
    global _worker_frames
    _worker_frames = frames


def _fit_period(frames: _WalkForwardFrames, period: list[date]) -> _PeriodResult:
    """Fit on the data before `period` (TRAIN_DAYS deep if set, after the first WARMUP_DAYS) and score `period`."""
    settings = SETTINGS.WEIGHTED_SCORE
    period_start = pd.Timestamp(period[0])
    train_start = (
        period_start - pd.Timedelta(days=settings.TRAIN_DAYS) if settings.TRAIN_DAYS else frames.warmed_up_start
    )
    is_train = np.asarray(
        (frames.history.index >= max(frames.warmed_up_start, train_start)) & (frames.history.index < period_start),
    )

    model = fit_model(frames.votes, frames.bars, is_train)
    is_in_period = np.isin(frames.bar_days, np.array(period))
    signal_bars = weighted_signal_bars(model, frames.votes[is_in_period], frames.history[is_in_period])

    is_scored = is_in_period & frames.is_scorable
    score = model.score(frames.votes[is_scored]).to_numpy()
    is_correlation_defined = score.std() > 0 and frames.target[is_scored].std() > 0
    correlation = float(np.corrcoef(score, frames.target[is_scored])[0, 1]) if is_correlation_defined else 0.0

    return _PeriodResult(signal_bars=signal_bars, correlation=correlation, kept_votes=len(model.weights))


def _fit_period_in_worker(period: list[date]) -> _PeriodResult:
    assert _worker_frames is not None, "the pool initializer sets the frames"
    return _fit_period(_worker_frames, period)


def _fit_periods_in_pool(frames: _WalkForwardFrames, periods: list[list[date]], workers: int) -> list[_PeriodResult]:
    with ProcessPoolExecutor(min(workers, len(periods)), initializer=_set_worker_frames, initargs=(frames,)) as pool:
        try:
            return list(pool.map(_fit_period_in_worker, periods))
        except BaseException:
            # Otherwise leaving the pool waits for every queued period before the error surfaces
            pool.shutdown(cancel_futures=True)
            raise


def weighted_walk_forward(
    history: pd.DataFrame,
    daily: pd.DataFrame,
    test_sessions: int,
    refit_sessions: int = 5,
    workers: int = 1,
) -> WeightedWalkForward:
    """Refit on everything before each period (TRAIN_DAYS deep if set, after the first WARMUP_DAYS), trade the next
    `refit_sessions` sessions with those weights, over the last `test_sessions` sessions of `history`. With
    `workers` > 1 the periods are fitted in that many processes."""
    settings = SETTINGS.WEIGHTED_SCORE
    bars = history[["Open", "High", "Low", "Close"]].copy()
    add_execution_columns(bars)
    bar_days = bar_index(history).date
    target = forward_move_bp(bars, settings.HORIZON_BARS)
    frames = _WalkForwardFrames(
        history=history,
        votes=vote_frame(history, daily),
        bars=bars,
        target=target,
        bar_days=bar_days,
        is_scorable=np.asarray(is_in_trading_window(bar_index(history)) & np.isfinite(target)),
        warmed_up_start=history.index[0].normalize() + pd.Timedelta(days=settings.WARMUP_DAYS),
    )

    test_days = sorted(set(bar_days))[-test_sessions:]
    periods = [test_days[offset : offset + refit_sessions] for offset in range(0, len(test_days), refit_sessions)]
    if workers > 1:
        period_results = _fit_periods_in_pool(frames, periods, workers)
    else:
        period_results = [_fit_period(frames, period) for period in periods]
    for period, result in zip(periods, period_results):
        log.debug(
            f"Weighted walk-forward {period[0]}: {result.kept_votes} votes, correlation {result.correlation:+.3f}",
        )

    sessions = replay(pd.concat([result.signal_bars for result in period_results]), set(test_days), WEIGHTED_LEVELS)
    return WeightedWalkForward(
        sessions=sessions,
        correlations=[result.correlation for result in period_results],
        kept_votes=[result.kept_votes for result in period_results],
    )
