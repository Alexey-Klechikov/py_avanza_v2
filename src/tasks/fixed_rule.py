import numpy as np
import pandas as pd

from config import SETTINGS
from services.ta.operators import get_indicators
from services.ta.strategies.models.signal import Signal
from services.ta.strategies.models.strategy import Strategy
from services.ta.strategies.signals import SIGNAL_COLUMNS, mark_strategy_signals, mask_outside_trading_time
from services.trading.tracked_position import ExitLevels
from tasks.backtest.bars import add_execution_columns

BAR_DURATION = pd.Timedelta(SETTINGS.RESOLUTION)
SIGNAL_DURATION = pd.Timedelta(SETTINGS.FIXED_RULE.SIGNAL_RESOLUTION)
OHLCV_AGGREGATION = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}

FIXED_RULE_LEVELS = ExitLevels(
    take_profit=SETTINGS.FIXED_RULE.TAKE_PROFIT,
    stop_loss=SETTINGS.FIXED_RULE.STOP_LOSS,
    pullback_trigger=SETTINGS.FIXED_RULE.PULLBACK_TRIGGER,
)


def _coarse_signal_flags(history: pd.DataFrame) -> pd.DataFrame:
    """SIGNAL_COLUMNS flags of the rule per SIGNAL_RESOLUTION bar (bar-start labels), LONG/SHORT already faded."""
    rule = SETTINGS.FIXED_RULE
    coarse = history.resample(SIGNAL_DURATION, label="left", closed="left").agg(OHLCV_AGGREGATION)
    coarse = coarse.dropna(subset=["Close"])

    indicators_mapping = get_indicators(coarse)
    selected_indicators = [tuple(name.split("-")) for name in rule.STRATEGY]
    strategy = Strategy(indicators_mapping=indicators_mapping, selected_indicators=selected_indicators)
    mark_strategy_signals(coarse, strategy, mask_trading_time=False)
    if rule.INVERTED:
        coarse = coarse.rename(columns={"LONG": "SHORT", "SHORT": "LONG"})

    return coarse[SIGNAL_COLUMNS].notna()


def fixed_rule_signal_bars(history: pd.DataFrame) -> pd.DataFrame:
    """2m bars (OHLC, "Next Open", "Day End", SIGNAL_COLUMNS) carrying the fixed rule's signals.

    `history` holds closed 2m bars only. A coarse bar's signal sits on the 2m bar that completes it, so it fills at
    that bar's "Next Open", and the trading window applies there. A coarse bar counts as complete once its last
    2m slot has closed or a later bar exists, so a coarse bar still in progress never signals.
    """
    completing_bars = (
        pd.Series(history.index, index=history.index).groupby(history.index.floor(SIGNAL_DURATION)).last()
    )
    is_complete = (completing_bars + BAR_DURATION >= completing_bars.index + SIGNAL_DURATION) | (
        completing_bars < history.index[-1]
    )
    completing_bars = completing_bars[is_complete]
    coarse_flags = _coarse_signal_flags(history).reindex(completing_bars.index, fill_value=False)

    bars = history[["Open", "High", "Low", "Close"]].copy()
    for column in SIGNAL_COLUMNS:
        signal_index = completing_bars[coarse_flags[column]].to_numpy()
        bars[column] = np.nan
        bars.loc[signal_index, column] = bars.loc[signal_index, "Close"]

    mask_outside_trading_time(bars)
    add_execution_columns(bars)

    return bars


def fixed_rule_signal(closed_history: pd.DataFrame) -> Signal | None:
    """The fixed rule's signal on the newest bar of `closed_history` (closed 2m bars, WARMUP_DAYS deep)."""
    last_bar = fixed_rule_signal_bars(closed_history)[SIGNAL_COLUMNS].iloc[-1]

    return Signal.from_bar(*last_bar.notna())
