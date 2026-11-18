import numpy as np
import pandas as pd

from config import SETTINGS
from services.ta.operators import get_indicators
from services.ta.strategies.models.signal import Signal
from services.ta.strategies.models.strategy import Strategy
from services.ta.strategies.signals import SIGNAL_COLUMNS, mark_strategy_signals, mask_outside_trading_time
from services.trading.tracked_position import ExitLevels
from tasks.backtest.bars import add_execution_columns
from tasks.coarse_bars import completing_bars, resample_ohlcv

SIGNAL_DURATION = pd.Timedelta(SETTINGS.FIXED_RULE.SIGNAL_RESOLUTION)

FIXED_RULE_LEVELS = ExitLevels(
    take_profit=SETTINGS.FIXED_RULE.TAKE_PROFIT,
    stop_loss=SETTINGS.FIXED_RULE.STOP_LOSS,
    pullback_trigger=SETTINGS.FIXED_RULE.PULLBACK_TRIGGER,
)


def _coarse_signal_flags(history: pd.DataFrame) -> pd.DataFrame:
    """SIGNAL_COLUMNS flags of the rule per SIGNAL_RESOLUTION bar (bar-start labels), LONG/SHORT already faded."""
    rule = SETTINGS.FIXED_RULE
    coarse = resample_ohlcv(history, SIGNAL_DURATION)

    indicators_mapping = get_indicators(coarse)
    selected_indicators = [
        (category, name) for category, name in (indicator.split("-", 1) for indicator in rule.STRATEGY)
    ]
    strategy = Strategy(indicators_mapping=indicators_mapping, selected_indicators=selected_indicators)
    mark_strategy_signals(coarse, strategy, mask_trading_time=False)
    if rule.INVERTED:
        coarse = coarse.rename(columns={"LONG": "SHORT", "SHORT": "LONG"})

    return coarse[SIGNAL_COLUMNS].notna()


def fixed_rule_signal_bars(history: pd.DataFrame) -> pd.DataFrame:
    """2m bars (OHLC, "Next Open", "Day End", SIGNAL_COLUMNS) carrying the fixed rule's signals.

    `history` holds closed 2m bars only. A coarse bar's signal sits on the 2m bar that completes it, so it fills at
    that bar's "Next Open", and the trading window applies there; a coarse bar still in progress never signals.
    """
    signal_bars = completing_bars(history, SIGNAL_DURATION)
    coarse_flags = _coarse_signal_flags(history).reindex(signal_bars.index, fill_value=False)

    bars = history[["Open", "High", "Low", "Close"]].copy()
    for column in SIGNAL_COLUMNS:
        signal_index = signal_bars[coarse_flags[column]].to_numpy()
        bars[column] = np.nan
        bars.loc[signal_index, column] = bars.loc[signal_index, "Close"]

    mask_outside_trading_time(bars)
    add_execution_columns(bars)

    return bars


def fixed_rule_signal(closed_history: pd.DataFrame) -> Signal | None:
    """The fixed rule's signal on the newest bar of `closed_history` (closed 2m bars, WARMUP_DAYS deep)."""
    last_bar = fixed_rule_signal_bars(closed_history)[SIGNAL_COLUMNS].iloc[-1]

    return Signal.from_bar(*last_bar.notna())
