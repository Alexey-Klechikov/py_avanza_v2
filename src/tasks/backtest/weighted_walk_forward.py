from datetime import date

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
    warmed_up_start = history.index[0].normalize() + pd.Timedelta(days=settings.WARMUP_DAYS)
    is_scorable = is_in_trading_window(bar_index(history)) & np.isfinite(target)

    period_signal_bars, correlations, kept_votes = [], [], []
    for period_offset in range(0, len(test_days), refit_sessions):
        period = test_days[period_offset : period_offset + refit_sessions]
        period_start = pd.Timestamp(period[0])
        train_start = period_start - pd.Timedelta(days=settings.TRAIN_DAYS) if settings.TRAIN_DAYS else warmed_up_start
        is_train = np.asarray((history.index >= max(warmed_up_start, train_start)) & (history.index < period_start))

        model = fit_model(votes, bars, is_train)
        is_in_period = np.isin(bar_days, period)
        period_signal_bars.append(weighted_signal_bars(model, votes[is_in_period], history[is_in_period]))

        is_scored = is_in_period & is_scorable
        score = model.score(votes[is_scored]).to_numpy()
        is_correlation_defined = score.std() > 0 and target[is_scored].std() > 0
        correlations.append(float(np.corrcoef(score, target[is_scored])[0, 1]) if is_correlation_defined else 0.0)
        kept_votes.append(len(model.weights))
        log.debug(
            f"Weighted walk-forward {period[0]}: {len(model.weights)} votes, correlation {correlations[-1]:+.3f}",
        )

    sessions = replay(pd.concat(period_signal_bars), set(test_days), WEIGHTED_LEVELS)
    return WeightedWalkForward(sessions=sessions, correlations=correlations, kept_votes=kept_votes)
