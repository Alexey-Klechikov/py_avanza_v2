from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest import TestCase

from src.services.trading.strategy_trigger import SignalPick, StrategyTrigger

# The trigger is generic over signals; plain strings keep this test independent of services/ta
Signal = SimpleNamespace(LONG="LONG", SHORT="SHORT", EXIT="EXIT")
NOW = datetime(2026, 11, 17, 12, 0)
LOCK = timedelta(minutes=40)


def _strategy(rank: int):
    return SimpleNamespace(rank=rank)


class Test_StrategyTrigger(TestCase):
    def test_first_signal_in_rank_order_wins_and_triggers(self):
        trigger = StrategyTrigger(lock=LOCK)
        first, second = _strategy(1), _strategy(2)

        assert trigger.pick([(first, None), (second, Signal.LONG)], now=NOW) == SignalPick(second, Signal.LONG)
        assert trigger.strategy is second and trigger.triggered_at == NOW

    def test_lower_ranked_than_trigger_is_ignored(self):
        triggered, lower = _strategy(3), _strategy(5)
        trigger = StrategyTrigger(lock=LOCK, strategy=triggered, triggered_at=NOW)

        signal_pick = trigger.pick([(lower, Signal.SHORT)], now=NOW + timedelta(minutes=2))

        assert signal_pick == SignalPick(lower, None) and signal_pick.is_ignored
        assert trigger.strategy is triggered and trigger.triggered_at == NOW

    def test_same_or_higher_rank_takes_over(self):
        triggered, higher = _strategy(3), _strategy(1)
        trigger = StrategyTrigger(lock=LOCK, strategy=triggered, triggered_at=NOW)

        assert trigger.pick([(higher, Signal.EXIT)], now=NOW) == SignalPick(higher, Signal.EXIT)
        assert trigger.pick([(higher, Signal.LONG)], now=NOW) == SignalPick(higher, Signal.LONG)

    def test_no_signal(self):
        assert StrategyTrigger(lock=LOCK).pick([(_strategy(1), None)], now=NOW) is None

    def test_stops_evaluating_after_first_signal(self):
        evaluated_ranks = []

        def candidates():
            for rank in (1, 2, 3):
                evaluated_ranks.append(rank)
                yield _strategy(rank), Signal.LONG if rank == 2 else None

        StrategyTrigger(lock=LOCK).pick(candidates(), now=NOW)
        assert evaluated_ranks == [1, 2]

    def test_released_without_position_or_after_lock(self):
        trigger = StrategyTrigger(lock=LOCK, strategy=_strategy(1), triggered_at=NOW)

        trigger.release_if_stale(now=NOW + LOCK - timedelta(seconds=1), holds_position=True)
        assert trigger.strategy is not None

        trigger.release_if_stale(now=NOW + LOCK, holds_position=True)
        assert trigger.strategy is None and trigger.triggered_at is None

        trigger = StrategyTrigger(lock=LOCK, strategy=_strategy(1), triggered_at=NOW)
        trigger.release_if_stale(now=NOW, holds_position=False)
        assert trigger.strategy is None
