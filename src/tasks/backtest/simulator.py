from datetime import datetime

import numpy as np
import pandas as pd

from config import SETTINGS
from services.trading.tracked_position import ExitLevels, TrackedPosition
from tasks.backtest.wallet import SIDES_WITH_OPPOSITE, ClosedTrade, Side, Wallet


class BarSimulator:
    """Plays bars (BAR_COLUMNS + SIGNAL_COLUMNS) against a wallet.

    On each bar, held positions are checked for exits first (they were open during the bar), then signals open
    new positions at "Next Open". Opening one side closes the opposite one. New positions use `levels`
    (default: the live settings); with `levels.hold_bars`, no entry happens on a bar that started with a position.
    """

    def __init__(self, levels: ExitLevels = ExitLevels()) -> None:
        self.wallet = Wallet()
        self.levels = levels

    def step(self, bar: pd.Series, timestamp: datetime) -> list[ClosedTrade]:
        closed_trades = []
        closed_sides: set[Side] = set()
        held_at_start = not self.wallet.is_empty()

        for side, _ in SIDES_WITH_OPPOSITE:
            position = self.wallet.get(side)
            exit_price = None if position is None else self._exit_price(position, bar, timestamp)
            if exit_price is None:
                continue

            closed_trades.append(self.wallet.close(side, exit_price))
            closed_sides.add(side)

        if self.levels.hold_bars and held_at_start:
            return closed_trades

        for side, opposite_side in SIDES_WITH_OPPOSITE:
            if side in closed_sides or self.wallet.get(side) is not None:
                continue

            if not self._is_entry(bar, side, opposite_side):
                continue

            if self.wallet.get(opposite_side) is not None:
                closed_trades.append(self.wallet.close(opposite_side, bar["Next Open"]))

            self.wallet.set(
                side,
                TrackedPosition.open(is_long=side == "LONG", entry_price=bar["Next Open"], levels=self.levels),
            )

        return closed_trades

    @staticmethod
    def _exit_price(position: TrackedPosition, bar: pd.Series, timestamp: datetime) -> float | None:
        # The resting take-profit order can fill inside the bar, before any close-based decision
        if position.hit_take_profit(bar["High"], bar["Low"]):
            return position.take_profit_fill(bar["Open"])

        if bar["EXIT"] > 0:
            return bar["Next Open"]

        if position.confirm_stop_loss(bar["Close"]) or position.confirm_pullback(bar["Close"]):
            return bar["Next Open"]

        if position.confirm_hold_expiry():
            return bar["Next Open"]

        if bar["Day End"] or timestamp.time() >= SETTINGS.TIME.END:
            return bar["Next Open"]

        return None

    @staticmethod
    def _is_entry(bar: pd.Series, side: Side, opposite_side: Side) -> bool:
        return bar[side] > 0 and np.isnan(bar["EXIT"]) and np.isnan(bar[opposite_side]) and not bar["Day End"]
