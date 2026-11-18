from datetime import date

import numpy as np
import pandas as pd
from pydantic import BaseModel

from config import SETTINGS
from tasks.backtest.bars import add_execution_columns, bar_index
from tasks.backtest.model import WEIGHTED_LEVELS, fit_model, forward_move_bp, in_trading_window, weighted_signal_bars
from tasks.backtest.paper_trade import PaperSession, replay
from tasks.backtest.votes import vote_frame
from utils.logger.operators import get_logger

log = get_logger()


class WeightedWalkForward(BaseModel):
    """Out-of-sample result of refitting the weighted score every `refit_sessions` sessions on the data before."""

    sessions: dict[date, PaperSession]
    # Per refit period: correlation of the score with the HORIZON_BARS move it predicts, and votes kept
    correlations: list[float]
    kept_votes: list[int]


def weighted_walk_forward(
    history: pd.DataFrame,
    daily: pd.DataFrame,
    test_sessions: int,
    refit_sessions: int = 5,
) -> WeightedWalkForward:
    """Refit on everything before each period (TRAIN_DAYS deep if set, after the first WARMUP_DAYS), trade the next
    `refit_sessions` sessions with those weights, over the last `test_sessions` sessions of `history`."""
    settings = SETTINGS.WEIGHTED_SCORE
    votes = vote_frame(history, daily)
    bars = history[["Open", "High", "Low", "Close"]].copy()
    add_execution_columns(bars)
    target = forward_move_bp(bars, settings.HORIZON_BARS)

    bar_days = bar_index(history).date
    all_sessions = sorted(set(bar_days))
    test_days = all_sessions[-test_sessions:]
    warm = history.index[0].normalize() + pd.Timedelta(days=settings.WARMUP_DAYS)
    is_scored = in_trading_window(bar_index(history)) & np.isfinite(target)

    period_bars, correlations, kept_votes = [], [], []
    for first in range(0, len(test_days), refit_sessions):
        period = test_days[first : first + refit_sessions]
        period_start = pd.Timestamp(period[0])
        train_start = period_start - pd.Timedelta(days=settings.TRAIN_DAYS) if settings.TRAIN_DAYS else warm
        train = np.asarray((history.index >= max(warm, train_start)) & (history.index < period_start))

        model = fit_model(votes, bars, train)
        in_period = np.isin(bar_days, period)
        period_bars.append(weighted_signal_bars(model, votes[in_period], history[in_period]))

        scored = in_period & is_scored
        score = model.score(votes[scored]).to_numpy()
        correlations.append(float(np.corrcoef(score, target[scored])[0, 1]) if score.std() > 0 else 0.0)
        kept_votes.append(len(model.weights))
        log.debug(
            f"Weighted walk-forward {period[0]}: {len(model.weights)} votes, correlation {correlations[-1]:+.3f}",
        )

    sessions = replay(pd.concat(period_bars), set(test_days), WEIGHTED_LEVELS)
    return WeightedWalkForward(sessions=sessions, correlations=correlations, kept_votes=kept_votes)
