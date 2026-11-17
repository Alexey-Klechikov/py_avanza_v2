import numpy as np
import pandas as pd

from config import SETTINGS
from services.ta.strategies.models.strategy import Strategy

# Per-bar strategy signals: the bar close where the strategy signals, NaN elsewhere
SIGNAL_COLUMNS = ["LONG", "SHORT", "EXIT"]


def mark_strategy_signals(data: pd.DataFrame, strategy: Strategy) -> None:
    """Fill SIGNAL_COLUMNS with the bar close where the strategy signals and NaN elsewhere.

    LONG and SHORT need every indicator of the strategy to agree; EXIT needs any one. Bars outside the
    trading window (SETTINGS.TIME) never signal.
    """
    for column in SIGNAL_COLUMNS:
        data[column] = data["Close"]

    for column in SIGNAL_COLUMNS:
        combination_condition = all if column in ["LONG", "SHORT"] else any

        signal_methods = [
            indicator.signal.__getattribute__(column)
            for indicator in strategy.indicators_logic
            if indicator.signal.__getattribute__(column) is not None
        ]

        data[column] = data.apply(
            lambda row: (
                np.nan
                if not signal_methods
                or not combination_condition(signal_method(row) for signal_method in signal_methods)
                else row[column]
            ),
            axis=1,
        )

    for column in SIGNAL_COLUMNS:
        for non_trading_time in (
            ["00:00", SETTINGS.TIME.START.strftime("%H:%M")],
            [SETTINGS.TIME.END.strftime("%H:%M"), "23:59"],
        ):
            data.loc[data.between_time(non_trading_time[0], non_trading_time[1]).index, column] = np.nan


def strategy_signal_flags(data: pd.DataFrame, strategy: Strategy) -> np.ndarray:
    """Boolean (bars x SIGNAL_COLUMNS) matrix of where the strategy signals."""
    mark_strategy_signals(data, strategy)

    return data[SIGNAL_COLUMNS].notna().to_numpy()
