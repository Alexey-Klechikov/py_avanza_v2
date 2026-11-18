import pandas as pd

# Prices the simulator needs on every bar, after add_execution_columns
BAR_COLUMNS = ["Open", "High", "Low", "Close", "Next Open", "Day End"]


def bar_index(bars: pd.DataFrame | pd.Series) -> pd.DatetimeIndex:
    """The bars' start times. Bar frames and series (caches, resampled bars, votes) are always indexed by time."""
    index = bars.index
    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError(f"Bars need a DatetimeIndex, got {type(index).__name__}")

    return index


def add_execution_columns(data: pd.DataFrame) -> None:
    """Add "Day End" (a trading day's last bar) and "Next Open" (the price an order placed on this bar fills at).

    Orders fill at the next bar's open, except on a day's last bar, where they fill at its close: positions
    never carry overnight and no price gap between sessions leaks into a trade.
    """
    trading_dates = pd.Series(bar_index(data).date, index=data.index)
    data["Day End"] = trading_dates.ne(trading_dates.shift(-1))
    data["Next Open"] = data["Open"].shift(-1).where(~data["Day End"], data["Close"])
