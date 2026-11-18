from datetime import datetime
from unittest import TestCase

import numpy as np
import pandas as pd

from src.config import SETTINGS
from src.services.trading.tracked_position import ExitLevels, TrackedPosition
from src.tasks.backtest.bars import add_execution_columns, bar_index
from src.tasks.backtest.simulator import BarSimulator

ENTRY_PRICE = 1000.0
TAKE_PROFIT, STOP_LOSS, PULLBACK_TRIGGER = 0.045, 0.03, 0.0225
LEVELS = ExitLevels(take_profit=TAKE_PROFIT, stop_loss=STOP_LOSS, pullback_trigger=PULLBACK_TRIGGER)


def _take_profit(position: TrackedPosition) -> float:
    assert position.take_profit_price is not None
    return position.take_profit_price


def _stop_loss(position: TrackedPosition) -> float:
    assert position.stop_loss_price is not None
    return position.stop_loss_price


MIDDAY = datetime(2026, 11, 16, 12, 0)


def _bar(
    close: float = ENTRY_PRICE,
    high: float | None = None,
    low: float | None = None,
    next_open: float = ENTRY_PRICE,
    long: bool = False,
    short: bool = False,
    exit: bool = False,
    day_end: bool = False,
) -> pd.Series:
    return pd.Series(
        {
            "Open": close,
            "High": close if high is None else high,
            "Low": close if low is None else low,
            "Close": close,
            "Next Open": next_open,
            "Day End": day_end,
            "LONG": close if long else np.nan,
            "SHORT": close if short else np.nan,
            "EXIT": close if exit else np.nan,
        },
    )


def _simulator_holding(is_long: bool) -> tuple[BarSimulator, TrackedPosition]:
    simulator = BarSimulator(LEVELS)
    position = TrackedPosition.open(is_long=is_long, entry_price=ENTRY_PRICE, levels=LEVELS)
    simulator.wallet.set("LONG" if is_long else "SHORT", position)

    return simulator, position


class Test_BarSimulator(TestCase):
    def test_entry_fills_at_next_open(self):
        simulator = BarSimulator(LEVELS)

        assert simulator.step(_bar(long=True, next_open=1001), MIDDAY) == []
        assert simulator.wallet.long is not None and simulator.wallet.long.entry_price == 1001

    def test_no_entry_on_exit_conflict_or_day_end(self):
        for bar in (_bar(long=True, exit=True), _bar(long=True, day_end=True), _bar(long=True, short=True)):
            simulator = BarSimulator(LEVELS)
            simulator.step(bar, MIDDAY)

            assert simulator.wallet.is_empty()

    def test_exit_wins_over_same_bar_long(self):
        simulator, position = _simulator_holding(is_long=True)

        closed_trades = simulator.step(_bar(long=True, exit=True, next_open=1002), MIDDAY)

        assert [trade.profit for trade in closed_trades] == [position.profit(1002)]
        assert simulator.wallet.is_empty()

    def test_take_profit_fills_inside_bar(self):
        simulator, position = _simulator_holding(is_long=True)

        closed_trades = simulator.step(_bar(high=_take_profit(position) + 1), MIDDAY)

        assert [trade.profit for trade in closed_trades] == [position.profit(_take_profit(position))]
        assert closed_trades[0].capital_return == position.capital_return(_take_profit(position))

    def test_reverse_closes_opposite_at_next_open(self):
        simulator, short_position = _simulator_holding(is_long=False)

        closed_trades = simulator.step(_bar(long=True, next_open=999), MIDDAY)

        assert [trade.profit for trade in closed_trades] == [short_position.profit(999)]
        assert simulator.wallet.short is None and simulator.wallet.long is not None

    def test_trading_end_closes(self):
        simulator, _ = _simulator_holding(is_long=True)

        assert len(simulator.step(_bar(), datetime.combine(MIDDAY.date(), SETTINGS.TIME.END))) == 1


class Test_AddExecutionColumns(TestCase):
    def test_day_end_fills_at_close_never_next_session(self):
        index = pd.to_datetime(["2026-11-13 12:56", "2026-11-13 12:58", "2026-11-16 09:00"])
        bars = pd.DataFrame({"Open": [1.0, 2.0, 9.0], "Close": [1.5, 2.5, 9.5]}, index=index)

        add_execution_columns(bars)

        assert bars["Day End"].tolist() == [False, True, True]
        assert bars["Next Open"].tolist() == [2.0, 2.5, 9.5]


class Test_SameDayResolution(TestCase):
    def test_no_position_survives_a_session(self):
        """LONG on every bar of a half day and a full day: whatever opens must close on its own day."""
        index = pd.date_range("2026-11-13 09:00", "2026-11-13 12:58", freq="2min").append(
            pd.date_range("2026-11-16 09:00", "2026-11-16 17:28", freq="2min"),
        )
        bars = pd.DataFrame(
            {"Open": ENTRY_PRICE, "High": ENTRY_PRICE, "Low": ENTRY_PRICE, "Close": ENTRY_PRICE},
            index=index,
        )
        add_execution_columns(bars)
        times = bar_index(bars).time
        trading_hours = (times >= SETTINGS.TIME.START) & (times < SETTINGS.TIME.END)
        bars["LONG"] = np.where(trading_hours, ENTRY_PRICE, np.nan)
        bars["SHORT"] = np.nan
        bars["EXIT"] = np.nan

        simulator = BarSimulator(LEVELS)
        closed_trades = 0
        for timestamp, bar in zip(bar_index(bars), (row for _, row in bars.iterrows())):
            closed_trades += len(simulator.step(bar, timestamp.to_pydatetime()))
            if bar["Day End"]:
                assert simulator.wallet.is_empty(), f"position carried past {timestamp}"

        assert closed_trades == 2  # one trade per session, each closed the same day


class Test_TimeBoxedPositions(TestCase):
    def test_exit_after_hold_bars_and_no_entries_meanwhile(self):
        simulator = BarSimulator(ExitLevels(take_profit=None, stop_loss=None, pullback_trigger=None, hold_bars=3))

        assert simulator.step(_bar(long=True, next_open=1000), MIDDAY) == []  # entry fills at 1000
        assert simulator.step(_bar(short=True, next_open=990), MIDDAY) == []  # held bar 1: opposite signal ignored
        assert simulator.step(_bar(long=True, next_open=1005), MIDDAY) == []  # held bar 2
        closed = simulator.step(_bar(short=True, next_open=1010), MIDDAY)  # held bar 3: exit at its next open

        assert len(closed) == 1 and closed[0].capital_return > 0
        assert simulator.wallet.is_empty()  # no entry on the exit bar either
