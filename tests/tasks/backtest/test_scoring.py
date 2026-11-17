from datetime import date, timedelta
from unittest import TestCase

from services.ta.strategies.models.strategy import TradeStats
from tasks.backtest.scoring import EdgeScorer, TradeHistory, training_rank, wilson_lower_bound

AS_OF = date(2026, 11, 17)
NO_DECAY = float("inf")


def _expected_edge(trades: list[tuple[date, float]], half_life_days: float = 30.0, prior_trades: float = 0.0) -> float:
    history = TradeHistory.from_stats(TradeStats(trade_returns=trades))

    return EdgeScorer(half_life_days=half_life_days, prior_trades=prior_trades).expected_edge(history, AS_OF)


def _days_ago(days: int) -> date:
    return AS_OF - timedelta(days=days)


class Test_EdgeScorer(TestCase):
    def test_no_trades(self):
        assert _expected_edge([]) == 0.0

    def test_unweighted_mean_without_decay_or_prior(self):
        trades = [(_days_ago(1), 0.02), (_days_ago(2), -0.01), (_days_ago(3), 0.02)]

        assert abs(_expected_edge(trades, half_life_days=NO_DECAY) - 0.01) < 1e-12

    def test_ignores_trades_closed_on_or_after_as_of(self):
        trades = [(_days_ago(1), 0.01), (AS_OF, 5.0), (AS_OF + timedelta(days=1), 5.0)]

        assert abs(_expected_edge(trades, half_life_days=NO_DECAY) - 0.01) < 1e-12

    def test_recent_trades_weigh_more(self):
        good_then_bad = [(_days_ago(60), 0.02), (_days_ago(1), -0.02)]

        assert _expected_edge(good_then_bad, half_life_days=10) < 0
        assert abs(_expected_edge(good_then_bad, half_life_days=NO_DECAY)) < 1e-12

    def test_prior_shrinks_small_samples_more(self):
        one_lucky_trade = [(_days_ago(1), 0.05)]
        steady_record = [(_days_ago(days), 0.01) for days in range(1, 31)]

        assert _expected_edge(one_lucky_trade) > _expected_edge(steady_record)
        assert _expected_edge(one_lucky_trade, prior_trades=10) < _expected_edge(steady_record, prior_trades=10)


class Test_TrainingRank(TestCase):
    def test_few_lucky_trades_rank_below_a_long_record(self):
        lucky = TradeStats(total_trades=2, total_profit=26.84, profitable_trades=2)
        steady = TradeStats(total_trades=10, total_profit=31.8, profitable_trades=7)

        assert training_rank(steady) > training_rank(lucky)

    def test_unprofitable_ranks_last(self):
        losing = TradeStats(total_trades=30, total_profit=-1, profitable_trades=20)
        barely_profitable = TradeStats(total_trades=3, total_profit=1, profitable_trades=1)

        assert training_rank(losing) < training_rank(barely_profitable)

    def test_wilson_lower_bound_is_pessimistic_for_small_samples(self):
        assert wilson_lower_bound(0, 0) == 0.0
        assert wilson_lower_bound(2, 2) < wilson_lower_bound(70, 100) < 0.7
