from datetime import date, timedelta
from types import SimpleNamespace
from unittest import TestCase

from src.services.ta.strategies.models.strategy import TradeStats
from src.tasks.backtest.scoring import EdgeScorer
from src.tasks.backtest.selection import select_daily_strategies, select_training_strategies

AS_OF = date(2026, 11, 17)
YESTERDAY = AS_OF - timedelta(days=1)


def _strategy(
    name: str,
    trades: int,
    profit: float,
    wins: int,
    indicators: tuple[str, ...] = (),
    original: bool = False,
    capital_return: float | None = None,
):
    return SimpleNamespace(
        name=name,
        original=original,
        selected_indicators=[("Category", indicator) for indicator in indicators or (name,)],
        trade_stats=TradeStats(
            total_trades=trades,
            total_profit=profit,
            profitable_trades=wins,
            trade_returns=[] if capital_return is None else [(YESTERDAY, capital_return)] * trades,
        ),
    )


class Test_SelectTrainingStrategies(TestCase):
    def test_min_trades_filters(self):
        few_trades = _strategy("few", trades=4, profit=50, wins=4)
        enough_trades = _strategy("enough", trades=6, profit=5, wins=4)

        assert select_training_strategies([few_trades, enough_trades], min_trades=5) == [enough_trades]

    def test_fallback_prefers_strategies_with_enough_trades(self):
        few_trades = _strategy("few", trades=2, profit=-1, wins=1)
        enough_trades = _strategy("enough", trades=30, profit=-5, wins=10)

        assert select_training_strategies([few_trades, enough_trades], min_trades=20) == [enough_trades]

    def test_parent_kept_when_only_low_trade_children_beat_it(self):
        parent = _strategy("parent", trades=25, profit=10, wins=15, indicators=("a", "b"), original=True)
        child = _strategy("child", trades=3, profit=100, wins=3, indicators=("a", "b", "c"))

        assert select_training_strategies([parent, child], min_trades=20) == [parent]


class Test_SelectDailyStrategies(TestCase):
    scorer = EdgeScorer(half_life_days=30, prior_trades=10)

    def test_ranks_by_expected_edge_and_drops_at_or_below_min_edge(self):
        strong = _strategy("strong", trades=20, profit=1, wins=15, capital_return=0.010)
        weak = _strategy("weak", trades=20, profit=1, wins=12, capital_return=0.002)
        losing = _strategy("losing", trades=20, profit=-1, wins=5, capital_return=-0.010)
        idle = _strategy("idle", trades=0, profit=0, wins=0)

        scored = select_daily_strategies([weak, losing, idle, strong], as_of=AS_OF, scorer=self.scorer, min_edge=0.0)

        assert [scored_strategy.strategy for scored_strategy in scored] == [strong, weak]
        assert scored[0].expected_edge > scored[1].expected_edge > 0

    def test_sits_out_when_nothing_clears_min_edge(self):
        weak = _strategy("weak", trades=20, profit=1, wins=12, capital_return=0.002)

        assert select_daily_strategies([weak], as_of=AS_OF, scorer=self.scorer, min_edge=0.01) == []
