from dataclasses import dataclass
from datetime import date
from itertools import combinations, product

import numpy as np
import pandas as pd
from pathos.multiprocessing import ProcessingPool as Pool
from pydantic import BaseModel

from services.ta.operators import get_indicators
from services.ta.strategies.models.strategy import Strategy
from tasks.backtest.scoring import EdgeScorer, TradeHistory
from tasks.backtest.simulator import simulate_strategy


@dataclass(frozen=True)
class WalkForwardGrid:
    """Selection settings to compare, and how the daily pick is simulated."""

    half_lives_days: tuple[float, ...] = (10, 20, 40, 80, float("inf"))
    prior_trades: tuple[float, ...] = (0, 10, 30)
    min_edges: tuple[float, ...] = (0.0, 0.0005, 0.001, 0.002)
    picks_per_day: int = 5
    warm_up_days: int = 60


class WalkForwardResult(BaseModel):
    """Outcome of one grid setting. Returns are fractions of capital at the nominal multiplier, after costs."""

    half_life_days: float
    prior_trades: float
    min_edge: float
    rank_correlation: float  # mean daily Spearman correlation of expected edge vs that day's return
    traded_days_share: float
    winning_days_share: float  # among traded days
    average_traded_day_return: float
    total_return: float


class SelectionWalkForward:
    """Replays the daily strategy selection over history.

    Each day, every candidate is scored on trades closed before that day; the best `picks_per_day` above the
    minimum edge are traded and their average return that day is booked (no pick: sit out, return 0).
    """

    def __init__(self, candidates: list[Strategy], trading_days: list[date], grid: WalkForwardGrid) -> None:
        self.grid = grid
        self.evaluated_days = trading_days[grid.warm_up_days :]
        self.histories = [TradeHistory.from_stats(candidate.trade_stats) for candidate in candidates]
        self.daily_returns = _daily_returns(candidates, trading_days)

    @classmethod
    def from_indicator_combinations(
        cls,
        data: pd.DataFrame,
        indicators_count: int,
        grid: WalkForwardGrid,
    ) -> "SelectionWalkForward":
        """Candidates are all `indicators_count`-indicator combinations, so no earlier selection biases the pool."""
        trading_days = sorted(set(data.index.date))
        indicators_mapping = get_indicators(data)
        indicators = [(category, name) for category, names in indicators_mapping.items() for name in names]
        candidates = [
            Strategy(indicators_mapping=indicators_mapping, selected_indicators=list(combination))
            for combination in combinations(indicators, indicators_count)
        ]

        with Pool() as pool:
            candidates = list(pool.map(simulate_strategy, [data] * len(candidates), candidates))

        return cls(candidates, trading_days, grid)

    @property
    def average_candidate_daily_return(self) -> float:
        return float(self.daily_returns.loc[self.evaluated_days].mean(axis=1).mean())

    def run(self) -> list[WalkForwardResult]:
        return [
            result
            for half_life_days, prior_trades in product(self.grid.half_lives_days, self.grid.prior_trades)
            for result in self._evaluate(half_life_days, prior_trades)
        ]

    def _evaluate(self, half_life_days: float, prior_trades: float) -> list[WalkForwardResult]:
        scorer = EdgeScorer(half_life_days=half_life_days, prior_trades=prior_trades)
        day_returns: dict[float, list[float | None]] = {min_edge: [] for min_edge in self.grid.min_edges}
        rank_correlations = []

        for day in self.evaluated_days:
            realized = self.daily_returns.loc[day]
            edges = pd.Series([scorer.expected_edge(history, as_of=day) for history in self.histories])
            if edges.std() > 0 and realized.std() > 0:
                rank_correlations.append(edges.rank().corr(realized.rank()))

            for min_edge in self.grid.min_edges:
                picks = edges[edges > min_edge].nlargest(self.grid.picks_per_day).index
                day_returns[min_edge].append(float(realized[picks].mean()) if len(picks) else None)

        return [
            _summarize(half_life_days, prior_trades, min_edge, returns, rank_correlations)
            for min_edge, returns in day_returns.items()
        ]


def _daily_returns(candidates: list[Strategy], trading_days: list[date]) -> pd.DataFrame:
    """Sum of each candidate's closed-trade capital returns per day (columns are candidate positions)."""
    columns = {}
    for position, candidate in enumerate(candidates):
        trades = candidate.trade_stats.trade_returns
        returns = pd.Series([r for _, r in trades], index=[closed_on for closed_on, _ in trades], dtype=float)
        columns[position] = returns.groupby(level=0).sum()

    return pd.DataFrame(columns).reindex(trading_days).fillna(0.0)


def _summarize(
    half_life_days: float,
    prior_trades: float,
    min_edge: float,
    day_returns: list[float | None],
    rank_correlations: list[float],
) -> WalkForwardResult:
    traded = np.array([day_return for day_return in day_returns if day_return is not None])
    booked = np.array([day_return or 0.0 for day_return in day_returns])

    return WalkForwardResult(
        half_life_days=half_life_days,
        prior_trades=prior_trades,
        min_edge=min_edge,
        rank_correlation=float(np.mean(rank_correlations)) if rank_correlations else 0.0,
        traded_days_share=len(traded) / len(booked) if len(booked) else 0.0,
        winning_days_share=float((traded > 0).mean()) if len(traded) else 0.0,
        average_traded_day_return=float(traded.mean()) if len(traded) else 0.0,
        total_return=float(booked.sum()),
    )
