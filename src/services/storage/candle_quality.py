from dataclasses import dataclass
from datetime import date

import pandas as pd

from config import SETTINGS

# A day needs this many bars before its candle quality can be judged
MIN_BARS_TO_JUDGE_DAY = 20


class DataQualityError(Exception):
    """Too little clean data to backtest on: calibrating would fit strategies to broken candles."""


@dataclass(frozen=True)
class CandleQuality:
    """Per-day verdict on whether the cached 2-minute candles are complete.

    A complete candle closes where the next one opens, so the jump between them is small next to a candle's own
    high-low range. A candle stored while still in progress (a snapshot of its first seconds) has a tiny range and
    a large jump to the next open. Days whose median jump exceeds their median range are partial-candle days.
    """

    clean_days: list[date]
    partial_days: list[date]

    @classmethod
    def of(cls, bars: pd.DataFrame) -> "CandleQuality":
        trading_dates = pd.Series(bars.index.date, index=bars.index)
        is_same_day_as_next = trading_dates.eq(trading_dates.shift(-1))
        candle_range = bars["High"] - bars["Low"]
        jump_to_next_open = (bars["Open"].shift(-1) - bars["Close"]).abs()

        per_day = pd.DataFrame(
            {"range": candle_range[is_same_day_as_next], "jump": jump_to_next_open[is_same_day_as_next]},
        ).groupby(trading_dates[is_same_day_as_next])
        medians = per_day.median()
        judged = per_day.size() >= MIN_BARS_TO_JUDGE_DAY
        is_partial = judged & (medians["jump"] > medians["range"])

        return cls(
            clean_days=sorted(day for day in set(bars.index.date) if not is_partial.get(day, False)),
            partial_days=sorted(day for day, partial in is_partial.items() if partial),
        )

    @property
    def clean_share(self) -> float:
        total_days = len(self.clean_days) + len(self.partial_days)
        return len(self.clean_days) / total_days if total_days else 0.0


def require_clean_bars(
    bars: pd.DataFrame, min_clean_share: float = SETTINGS.STRATEGY.MIN_CLEAN_DAY_SHARE
) -> pd.DataFrame:
    """Bars of the clean days only. Raises DataQualityError when clean days are below `min_clean_share`."""
    quality = CandleQuality.of(bars)
    if quality.clean_share < min_clean_share:
        first_partial_day = quality.partial_days[0] if quality.partial_days else "none"
        raise DataQualityError(
            f"Only {len(quality.clean_days)} of {len(quality.clean_days) + len(quality.partial_days)} days have "
            f"complete candles (need {min_clean_share:.0%}); first partial day {first_partial_day}. "
            "Repair the cache with task_repair_history.py or wait for clean days to accumulate.",
        )

    clean_days = set(quality.clean_days)
    return bars[[bar_day in clean_days for bar_day in bars.index.date]]
