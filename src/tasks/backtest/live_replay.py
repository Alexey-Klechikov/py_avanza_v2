from datetime import datetime

import numpy as np
import pandas as pd
from pathos.multiprocessing import ProcessingPool as Pool

from services.ta.strategies.models.signal import Signal
from services.ta.strategies.models.strategy import Strategy, TradeStats
from services.ta.strategies.signals import SIGNAL_COLUMNS, strategy_signal_flags
from services.trading.strategy_trigger import StrategyTrigger
from tasks.backtest.bars import BAR_COLUMNS, add_execution_columns
from tasks.backtest.simulator import BarSimulator


def replay_live_selection(data: pd.DataFrame, strategies: list[Strategy]) -> TradeStats:
    """Trade the stored strategies the way the live loop does.

    On each bar the first strategy in rank order with a signal wins, and StrategyTrigger ignores lower-ranked
    strategies while the last triggered one holds the lock.
    """
    stats = TradeStats()
    if not strategies:
        return stats

    add_execution_columns(data)
    with Pool() as pool:
        signal_flags: list[np.ndarray] = list(pool.map(strategy_signal_flags, [data] * len(strategies), strategies))

    simulator = BarSimulator()
    trigger = StrategyTrigger.from_settings()

    for bar_number, (index, bar) in enumerate(data[BAR_COLUMNS].iterrows()):
        timestamp: datetime = index.to_pydatetime()  # type: ignore
        trigger.release_if_stale(now=timestamp, holds_position=not simulator.wallet.is_empty())

        candidates = (
            (strategy, Signal.from_bar(*flags[bar_number])) for strategy, flags in zip(strategies, signal_flags)
        )
        signal_pick = trigger.pick(candidates, now=timestamp)
        signal = signal_pick.signal if signal_pick else None

        for closed_trade in simulator.step(_bar_with_signal(bar, signal), timestamp):
            stats.record(closed_trade.profit, closed_trade.capital_return, closed_on=timestamp.date())

    return stats


def _bar_with_signal(bar: pd.Series, signal: Signal | None) -> pd.Series:
    bar = bar.copy()
    for column in SIGNAL_COLUMNS:
        bar[column] = bar["Close"] if signal and signal.value == column else np.nan

    return bar
