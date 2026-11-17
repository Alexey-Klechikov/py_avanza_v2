import math
from dataclasses import dataclass
from datetime import date

import numpy as np

from config import SETTINGS
from services.ta.strategies.models.strategy import TradeStats

WILSON_Z = 1.96  # 95% interval


@dataclass(frozen=True)
class TradeHistory:
    """A strategy's closed trades as sorted arrays, ready for repeated scoring."""

    closed_on: np.ndarray  # datetime64[D], ascending
    capital_returns: np.ndarray

    @classmethod
    def from_stats(cls, stats: TradeStats) -> "TradeHistory":
        trades = sorted(stats.trade_returns)

        return cls(
            closed_on=np.array([closed_on for closed_on, _ in trades], dtype="datetime64[D]"),
            capital_returns=np.array([capital_return for _, capital_return in trades], dtype=float),
        )


@dataclass(frozen=True)
class EdgeScorer:
    """Expected capital return of a strategy's next trade.

    The mean return of trades closed before `as_of`, where each trade's weight halves every `half_life_days`,
    shrunk toward zero by `prior_trades` zero-return pseudo-trades so small samples cannot look certain.
    """

    half_life_days: float
    prior_trades: float

    @classmethod
    def from_settings(cls) -> "EdgeScorer":
        return cls(
            half_life_days=SETTINGS.STRATEGY.SCORE_HALF_LIFE_DAYS,
            prior_trades=SETTINGS.STRATEGY.SCORE_PRIOR_TRADES,
        )

    def expected_edge(self, history: TradeHistory, as_of: date) -> float:
        as_of_day = np.datetime64(as_of, "D")
        past_trades = np.searchsorted(history.closed_on, as_of_day)
        if past_trades == 0:
            return 0.0

        ages_days = (as_of_day - history.closed_on[:past_trades]).astype(float)
        weights = 0.5 ** (ages_days / self.half_life_days)

        return float((weights * history.capital_returns[:past_trades]).sum() / (weights.sum() + self.prior_trades))


def wilson_lower_bound(successes: int, trials: int) -> float:
    """Lower bound of the 95% Wilson interval of a success share: small samples get a pessimistic share."""
    if trials == 0:
        return 0.0

    share = successes / trials
    z_squared = WILSON_Z**2
    centre = share + z_squared / (2 * trials)
    margin = WILSON_Z * math.sqrt(share * (1 - share) / trials + z_squared / (4 * trials**2))

    return (centre - margin) / (1 + z_squared / trials)


def training_rank(stats: TradeStats) -> tuple[bool, float]:
    """Sort key for training: profitable first, then profit weighted by a lower-bound win share."""
    if stats.total_profit <= 0:
        return False, stats.total_profit

    return True, stats.total_profit * wilson_lower_bound(stats.profitable_trades, stats.total_trades)
