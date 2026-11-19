from collections.abc import Iterator
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import dataclass
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


@dataclass(frozen=True)
class _TuningInputs:
    """What every run of one tuning shares; `indicators` is the parent's SETTINGS.INDICATORS, which a worker process
    would otherwise re-read from settings.py."""

    history: pd.DataFrame
    daily: pd.DataFrame
    grid: IndicatorGrid
    indicators: dict
    test_sessions: int
    refit_sessions: int


# A worker process receives the inputs once through the pool initializer, not once per candidate
_worker_inputs: _TuningInputs | None = None


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


def _set_worker_inputs(inputs: _TuningInputs) -> None:
    global _worker_inputs
    _worker_inputs = inputs
    SETTINGS.INDICATORS.clear()
    SETTINGS.INDICATORS.update(inputs.indicators)


def _run_candidate(inputs: _TuningInputs, label: str, params: dict | None) -> TuningResult:
    """Walk-forward with `params` for the grid's indicator (None: off); SETTINGS.INDICATORS is restored afterwards."""
    indicators = SETTINGS.INDICATORS[inputs.grid.category]
    saved_params = indicators.pop(inputs.grid.name, None)
    if params:
        indicators[inputs.grid.name] = params
    try:
        walk_forward = weighted_walk_forward(inputs.history, inputs.daily, inputs.test_sessions, inputs.refit_sessions)
    finally:
        indicators.pop(inputs.grid.name, None)
        if saved_params:
            indicators[inputs.grid.name] = saved_params

    return _tuning_result(label, params or {}, walk_forward)


def _run_candidate_in_worker(label: str, params: dict | None) -> TuningResult:
    assert _worker_inputs is not None, "the pool initializer sets the inputs"
    return _run_candidate(_worker_inputs, label, params)


def _completed_results(
    inputs: _TuningInputs,
    runs: list[tuple[str, dict | None]],
    workers: int,
) -> Iterator[TuningResult]:
    """Results of `runs` as they finish: in order without a pool, else from `workers` processes."""
    if workers <= 1:
        yield from (_run_candidate(inputs, label, params) for label, params in runs)
        return

    with ProcessPoolExecutor(min(workers, len(runs)), initializer=_set_worker_inputs, initargs=(inputs,)) as pool:
        futures = [pool.submit(_run_candidate_in_worker, label, params) for label, params in runs]
        yield from (future.result() for future in as_completed(futures))


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
    workers: int = 1,
) -> list[TuningResult]:
    """Walk-forward the weighted score over `history` with the current parameters, the indicator off, and each
    candidate of `grid`, in `workers` processes; best edge first. SETTINGS.INDICATORS is unchanged afterwards."""
    indicators = SETTINGS.INDICATORS.get(grid.category)
    if indicators is None:
        raise ValueError(f"Unknown indicator category {grid.category!r}; known: {sorted(SETTINGS.INDICATORS)}")
    current_params = indicators.get(grid.name)
    runs: list[tuple[str, dict | None]] = [("current", current_params)] if current_params else []
    runs += [("off", None)] + [("", params) for params in grid.candidates() if params != current_params]
    inputs = _TuningInputs(
        history=history,
        daily=daily,
        grid=grid,
        indicators=deepcopy(SETTINGS.INDICATORS),
        test_sessions=full_training_sessions(history),
        refit_sessions=refit_sessions,
    )

    results = []
    for run_number, result in enumerate(_completed_results(inputs, runs, workers), start=1):
        results.append(result)
        log.info(
            f"[{run_number}/{len(runs)}] {grid.category}-{grid.name} {result.label or result.params}: "
            f"edge {result.edge:+.2f}, correlation {result.correlation:+.4f}, {result.trades} trades, "
            f"{100 * result.net_return_per_trade:+.2f}% net per trade",
        )

    return sorted(results, key=lambda result: result.edge, reverse=True)
