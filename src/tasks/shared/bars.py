import numpy as np
import pandas as pd

from config import SETTINGS

BAR_DURATION = pd.Timedelta(SETTINGS.RESOLUTION)
TRADING_START_MINUTE = SETTINGS.TIME.START.hour * 60 + SETTINGS.TIME.START.minute
TRADING_END_MINUTE = SETTINGS.TIME.END.hour * 60 + SETTINGS.TIME.END.minute

# Prices the simulator needs on every bar, after add_execution_columns
BAR_COLUMNS = ["Open", "High", "Low", "Close", "Next Open", "Day End"]


def bar_index(bars: pd.DataFrame | pd.Series) -> pd.DatetimeIndex:
    """The bars' start times. Bar frames and series (caches, resampled bars, votes) are always indexed by time."""
    index = bars.index
    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError(f"Bars need a DatetimeIndex, got {type(index).__name__}")

    return index


def add_execution_columns(bars: pd.DataFrame) -> None:
    """Add "Day End" (a trading day's last bar) and "Next Open" (the price an order placed on this bar fills at).

    Orders fill at the next bar's open, except on a day's last bar, where they fill at its close: positions
    never carry overnight and no price gap between sessions leaks into a trade.
    """
    trading_dates = pd.Series(bar_index(bars).date, index=bars.index)
    bars["Day End"] = trading_dates.ne(trading_dates.shift(-1))
    bars["Next Open"] = bars["Open"].shift(-1).where(~bars["Day End"], bars["Close"])


def _end_minutes_of_day(bar_starts: pd.DatetimeIndex) -> np.ndarray:
    # Integer minutes, not datetime.time objects: this runs over every cached bar on each refit
    bar_ends = bar_starts + BAR_DURATION
    return np.asarray(bar_ends.hour * 60 + bar_ends.minute)


def is_in_trading_window(bar_starts: pd.DatetimeIndex) -> np.ndarray:
    """Bars the live loop acts on. It decides seconds after a bar closes and only while the clock is strictly inside
    SETTINGS.TIME, so a bar counts by its end time, not its start; the backtest follows the live loop."""
    end_minutes = _end_minutes_of_day(bar_starts)

    return (end_minutes > TRADING_START_MINUTE) & (end_minutes < TRADING_END_MINUTE)


def is_at_or_after_trading_end(bar_starts: pd.DatetimeIndex) -> np.ndarray:
    """Bars at whose close the live loop sells every position for the day (its first decision at or after END)."""
    return _end_minutes_of_day(bar_starts) >= TRADING_END_MINUTE
