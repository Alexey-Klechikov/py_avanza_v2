from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from config import SETTINGS


class RankedStrategy(Protocol):
    """Anything with a rank, where 1 is the best."""

    rank: int


@dataclass(frozen=True)
class SignalPick[StrategyT: RankedStrategy, SignalT]:
    """The first strategy (in rank order) that signalled on a bar. `signal` is None when it was ignored."""

    strategy: StrategyT
    signal: SignalT | None

    @property
    def is_ignored(self) -> bool:
        return self.signal is None


@dataclass
class StrategyTrigger[StrategyT: RankedStrategy, SignalT]:
    """Tracks the strategy whose signal was last acted on.

    While it holds the trigger, signals from lower-ranked strategies are ignored. The trigger is released after
    `lock` or when no position is held. Shared by the live loop and the backtest's live-selection replay.
    """

    lock: timedelta
    strategy: StrategyT | None = None
    triggered_at: datetime | None = None

    @classmethod
    def from_settings(cls) -> "StrategyTrigger[StrategyT, SignalT]":
        return cls(lock=timedelta(minutes=SETTINGS.STRATEGY.TRIGGER_LOCK_MINUTES))

    def release(self) -> None:
        self.strategy = None
        self.triggered_at = None

    def release_if_stale(self, now: datetime, holds_position: bool) -> None:
        lock_expired = self.triggered_at is not None and now - self.triggered_at >= self.lock
        if not holds_position or lock_expired:
            self.release()

    def pick(
        self,
        candidates: Iterable[tuple[StrategyT, SignalT | None]],
        now: datetime,
    ) -> SignalPick[StrategyT, SignalT] | None:
        """Take the first candidate with a signal; candidates are evaluated lazily, in rank order."""
        for strategy, signal in candidates:
            if signal is None:
                continue

            if self.strategy is not None and strategy.rank > self.strategy.rank:
                return SignalPick(strategy=strategy, signal=None)

            self.strategy = strategy
            self.triggered_at = now
            return SignalPick(strategy=strategy, signal=signal)

        return None
