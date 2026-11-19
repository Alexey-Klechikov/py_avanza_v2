from itertools import product

import numpy as np
import pandas as pd
from pydantic import BaseModel

from config import SETTINGS
from tasks.backtest.weighted_walk_forward import WeightedWalkForward, weighted_walk_forward
from tasks.shared.bars import bar_index
from utils.logger.operators import get_logger

log = get_logger()


class IndicatorGrid(BaseModel):
    """Parameters of one SETTINGS.INDICATORS entry to try: a list is searched, a scalar stays fixed."""

    category: str
    name: str
    params: dict[str, list | int | float | str]

    def candidates(self) -> list[dict]:
        choices = [value if isinstance(value, list) else [value] for value in self.params.values()]
        return [dict(zip(self.params, combination)) for combination in product(*choices)]


class TuningResult(BaseModel):
    """Out-of-sample quality of the weighted score with one parameter set (`params` empty: indicator off).

    `edge` is the unified score: the t-statistic of the score's correlation with the move it predicts, taken per
    refit period (mean / standard error). It measures how reliably the score predicts, independent of entry
    thresholds and costs; differences under ~1 are noise. The trade columns show what the entry threshold makes of
    it after SETTINGS.BACKTEST_SPREAD.
    """

    label: str
    params: dict
    edge: float
    correlation: float
    positive_periods: float
    trades: int
    net_return_per_trade: float  # fraction of position capital


def _tuning_result(label: str, params: dict, walk_forward: WeightedWalkForward) -> TuningResult:
    correlations = np.array(walk_forward.correlations)
    trade_returns = [trade_return for paper in walk_forward.sessions.values() for trade_return in paper.trade_returns]
    correlation_sd = correlations.std(ddof=1) if len(correlations) > 1 else 0.0

    return TuningResult(
        label=label,
        params=params,
        edge=float(correlations.mean() / correlation_sd * np.sqrt(len(correlations))) if correlation_sd > 0 else 0.0,
        correlation=float(correlations.mean()),
        positive_periods=float((correlations > 0).mean()),
        trades=len(trade_returns),
        net_return_per_trade=float(np.mean(trade_returns)) if trade_returns else 0.0,
    )


def full_training_sessions(history: pd.DataFrame) -> int:
    """Sessions of `history` whose walk-forward fit sees a full WARMUP_DAYS + TRAIN_DAYS before them."""
    settings = SETTINGS.WEIGHTED_SCORE
    session_days = np.unique(bar_index(history).normalize())
    first_full_day = session_days[0] + pd.Timedelta(days=settings.WARMUP_DAYS + settings.TRAIN_DAYS)

    return int((session_days >= first_full_day).sum())


def tune_indicator(
    history: pd.DataFrame,
    daily: pd.DataFrame,
    grid: IndicatorGrid,
    refit_sessions: int = 5,
) -> list[TuningResult]:
    """Walk-forward the weighted score over `history` with the current parameters, the indicator off, and each
    candidate of `grid`; best edge first. SETTINGS.INDICATORS is restored afterwards."""
    indicators = SETTINGS.INDICATORS.get(grid.category)
    if indicators is None:
        raise ValueError(f"Unknown indicator category {grid.category!r}; known: {sorted(SETTINGS.INDICATORS)}")
    current_params = indicators.get(grid.name)
    runs = [("current", current_params)] if current_params else []
    runs += [("off", None)] + [("", params) for params in grid.candidates() if params != current_params]
    test_sessions = full_training_sessions(history)

    results = []
    try:
        for run_number, (label, params) in enumerate(runs, start=1):
            indicators.pop(grid.name, None)
            if params:
                indicators[grid.name] = params

            result = _tuning_result(
                label,
                params or {},
                weighted_walk_forward(history, daily, test_sessions, refit_sessions),
            )
            results.append(result)
            log.info(
                f"[{run_number}/{len(runs)}] {grid.category}-{grid.name} {label or params}: edge {result.edge:+.2f}, "
                f"correlation {result.correlation:+.4f}, {result.trades} trades, "
                f"{100 * result.net_return_per_trade:+.2f}% net per trade",
            )
    finally:
        indicators.pop(grid.name, None)
        if current_params:
            indicators[grid.name] = current_params

    return sorted(results, key=lambda result: result.edge, reverse=True)
