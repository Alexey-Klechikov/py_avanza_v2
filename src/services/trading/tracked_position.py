from pydantic import BaseModel

from config import SETTINGS


class ExitLevels(BaseModel, frozen=True):
    """Exit parameters of a position, in instrument terms at the nominal MULTIPLIER (see SETTINGS.STOP_LOSS and
    SETTINGS.PULLBACK for the confirmation rules); None turns a rule off, and the default has none.

    `hold_bars` makes the position time-boxed: it exits at the next open once it has been held that many completed
    bars, and while it is held, new entry signals are ignored (backtest and live loop alike).
    """

    take_profit: float | None = None
    stop_loss: float | None = None
    pullback_trigger: float | None = None
    hold_bars: int | None = None


class TrackedPosition(BaseModel):
    """One open position and its exit levels, measured on the underlying so the backtest and the live loop agree.

    Prices are underlying (index) prices. The entry fills at the actual price; the spread is paid once, on the
    sale: the instrument is sold SETTINGS.SPREAD_DEFAULT below its actual price, so a flat exit loses exactly
    the spread.
    Stop-loss and pullback exits need consecutive confirmations; the counters belong to this position only.
    A level of None never triggers.
    """

    is_long: bool
    entry_price: float
    take_profit_price: float | None
    stop_loss_price: float | None
    instrument_leverage: float
    pullback_trigger: float | None = None
    hold_bars: int | None = None

    max_profit: float = 0
    stop_loss_confirmations: int = 0
    pullback_confirmations: int = 0
    bars_held: int = 0

    @classmethod
    def open(
        cls,
        is_long: bool,
        entry_price: float,
        instrument_leverage: float = SETTINGS.MULTIPLIER,
        levels: ExitLevels = ExitLevels(),
    ) -> "TrackedPosition":
        sign = 1 if is_long else -1
        take_profit, stop_loss = levels.take_profit, levels.stop_loss

        return cls(
            is_long=is_long,
            entry_price=entry_price,
            take_profit_price=(
                None if take_profit is None else entry_price * (1 + sign * take_profit / SETTINGS.MULTIPLIER)
            ),
            stop_loss_price=None if stop_loss is None else entry_price * (1 - sign * stop_loss / SETTINGS.MULTIPLIER),
            instrument_leverage=instrument_leverage or SETTINGS.MULTIPLIER,
            pullback_trigger=levels.pullback_trigger,
            hold_bars=levels.hold_bars,
        )

    @property
    def sign(self) -> int:
        return 1 if self.is_long else -1

    def capital_return(self, sell_price: float) -> float:
        """Net return on the capital in the position when sold at `sell_price` (underlying), at nominal leverage.

        The instrument moves `gross` before costs and is sold SPREAD_DEFAULT below its actual price at that moment:
        proceeds (1 + gross) * (1 - spread), so the net return is gross - spread * (1 + gross).
        """
        gross = self.sign * (sell_price / self.entry_price - 1) * SETTINGS.MULTIPLIER

        return gross - SETTINGS.SPREAD_DEFAULT * (1 + gross)

    def profit(self, sell_price: float) -> float:
        """Net profit in underlying points: the net capital return expressed as an underlying move from entry."""
        return self.capital_return(sell_price) * self.entry_price / SETTINGS.MULTIPLIER

    def hit_take_profit(self, high: float, low: float) -> bool:
        if self.take_profit_price is None:
            return False

        return high >= self.take_profit_price if self.is_long else low <= self.take_profit_price

    def take_profit_fill(self, open_price: float) -> float:
        """A resting limit order fills at the limit, or at the open when the bar gaps through it."""
        assert self.take_profit_price is not None
        if self.is_long:
            return max(self.take_profit_price, open_price)

        return min(self.take_profit_price, open_price)

    def instrument_take_profit_price(self, instrument_acquired_price: float) -> float | None:
        """Limit price on the bought instrument that matches the underlying take-profit level at its leverage."""
        if self.take_profit_price is None:
            return None

        underlying_move = self.sign * (self.take_profit_price / self.entry_price - 1)

        return instrument_acquired_price * (1 + self.instrument_leverage * underlying_move)

    def confirm_stop_loss(self, close_price: float) -> bool:
        if self.stop_loss_price is None:
            return False

        if self.sign * (close_price - self.stop_loss_price) >= 0:
            self.stop_loss_confirmations = 0
            return False

        self.stop_loss_confirmations += 1
        return self.stop_loss_confirmations > SETTINGS.STOP_LOSS.CONFIRMATION_COUNT

    def confirm_pullback(self, close_price: float) -> bool:
        if not self._is_pullback(close_price):
            self.pullback_confirmations = 0
            return False

        self.pullback_confirmations += 1
        return self.pullback_confirmations > SETTINGS.PULLBACK.CONFIRMATION_COUNT

    def confirm_hold_expiry(self) -> bool:
        """Count one more completed bar held; True once `hold_bars` bars are held. Call once per completed bar."""
        if self.hold_bars is None:
            return False

        self.bars_held += 1
        return self.bars_held >= self.hold_bars

    def _is_pullback(self, close_price: float) -> bool:
        if self.pullback_trigger is None:
            return False

        profit = self.profit(close_price)
        self.max_profit = max(self.max_profit, profit)

        trigger_profit = self.pullback_trigger * self.entry_price / SETTINGS.MULTIPLIER
        if self.max_profit <= trigger_profit:
            return False

        return profit < 0 or (self.max_profit - profit) / self.max_profit > SETTINGS.PULLBACK.VALUE
