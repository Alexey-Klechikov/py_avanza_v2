from dataclasses import dataclass
from datetime import date

from config import SETTINGS
from services.ta.strategies.models.strategy import Strategy
from tasks.backtest.scoring import EdgeScorer, TradeHistory, training_rank
from utils.logger.operators import get_logger

log = get_logger()

IndicatorSet = frozenset[tuple[str, str]]


@dataclass(frozen=True)
class ScoredStrategy:
    strategy: Strategy
    expected_edge: float


def select_training_strategies(strategies: list[Strategy], min_trades: int) -> list[Strategy]:
    """Profitable strategies with at least `min_trades` trades, best training rank first.

    A parent (an `original` strategy from the previous level) is kept unless one of its one-indicator extensions
    with enough trades ranks higher. With no qualifying strategy, the best FALLBACK_COUNT advance anyway so the
    next level can still find a winner.
    """
    traded = [
        strategy
        for strategy in _carry_unbeaten_parents(strategies, min_trades)
        if strategy.trade_stats.total_trades > 0
    ]
    ranked = sorted(traded, key=lambda strategy: training_rank(strategy.trade_stats), reverse=True)
    eligible = [strategy for strategy in ranked if strategy.trade_stats.total_trades >= min_trades]
    profitable = [strategy for strategy in eligible if strategy.trade_stats.total_profit > 0]
    if profitable:
        return profitable

    fallback = (eligible or ranked)[: SETTINGS.STRATEGY.FALLBACK_COUNT]
    log.warning(
        f"No profitable strategies with {min_trades}+ trades; keeping the top {len(fallback)} to extend further",
    )
    return fallback


def select_daily_strategies(
    strategies: list[Strategy],
    as_of: date,
    scorer: EdgeScorer | None = None,
    min_edge: float = SETTINGS.STRATEGY.MIN_EDGE,
) -> list[ScoredStrategy]:
    """Strategies whose expected edge on `as_of` exceeds `min_edge`, best first. Empty means sit out."""
    scorer = scorer or EdgeScorer.from_settings()
    scored = [
        ScoredStrategy(
            strategy=strategy,
            expected_edge=scorer.expected_edge(TradeHistory.from_stats(strategy.trade_stats), as_of),
        )
        for strategy in strategies
        if strategy.trade_stats.total_trades
    ]

    return sorted(
        (scored_strategy for scored_strategy in scored if scored_strategy.expected_edge > min_edge),
        key=lambda scored_strategy: scored_strategy.expected_edge,
        reverse=True,
    )


def _indicator_set(strategy: Strategy) -> IndicatorSet:
    return frozenset(strategy.selected_indicators)


def _parent_indicator_sets(strategy: Strategy) -> set[IndicatorSet]:
    indicators = _indicator_set(strategy)
    return {indicators - {indicator} for indicator in indicators}


def _carry_unbeaten_parents(strategies: list[Strategy], min_trades: int) -> list[Strategy]:
    parents = {_indicator_set(strategy): strategy for strategy in strategies if strategy.original}
    children = [strategy for strategy in strategies if not strategy.original]

    best_child_ranks: dict[IndicatorSet, tuple[bool, float]] = {}
    for child in children:
        if child.trade_stats.total_trades < min_trades:
            continue

        child_rank = training_rank(child.trade_stats)
        for parent_indicators in parents.keys() & _parent_indicator_sets(child):
            best_child_ranks[parent_indicators] = max(best_child_ranks.get(parent_indicators, child_rank), child_rank)

    unbeaten_parents = [
        parent
        for parent_indicators, parent in parents.items()
        if parent_indicators not in best_child_ranks
        or best_child_ranks[parent_indicators] <= training_rank(parent.trade_stats)
    ]
    for parent in unbeaten_parents:
        parent.original = False

    return unbeaten_parents + children
