from pydantic import BaseModel

from config import SETTINGS


class TrackedPosition(BaseModel):
    """One open position and its exit levels, measured on the underlying so the backtest and the live loop agree.

    Prices are underlying (index) prices. `buy_price` includes SETTINGS.ROUND_TRIP_COST (spread and commission), so
    a flat exit loses exactly that cost.
    Stop-loss and pullback exits need consecutive confirmations; the counters belong to this position only.
    """

    is_long: bool
    entry_price: float
    buy_price: float
    take_profit_price: float
    stop_loss_price: float
    instrument_leverage: float

    max_profit: float = 0
    stop_loss_confirmations: int = 0
    pullback_confirmations: int = 0

    @classmethod
    def open(
        cls,
        is_long: bool,
        entry_price: float,
        instrument_leverage: float = SETTINGS.MULTIPLIER,
    ) -> "TrackedPosition":
        sign = 1 if is_long else -1

        return cls(
            is_long=is_long,
            entry_price=entry_price,
            buy_price=entry_price * (1 + sign * SETTINGS.ROUND_TRIP_COST / SETTINGS.MULTIPLIER),
            take_profit_price=entry_price * (1 + sign * SETTINGS.TAKE_PROFIT.VALUE / SETTINGS.MULTIPLIER),
            stop_loss_price=entry_price * (1 - sign * SETTINGS.STOP_LOSS.VALUE / SETTINGS.MULTIPLIER),
            instrument_leverage=instrument_leverage or SETTINGS.MULTIPLIER,
        )

    @property
    def sign(self) -> int:
        return 1 if self.is_long else -1

    def profit(self, sell_price: float) -> float:
        """Profit in underlying points."""
        return self.sign * (sell_price - self.buy_price)

    def capital_return(self, sell_price: float) -> float:
        """Profit as a fraction of the capital in the position, at the nominal leverage."""
        return self.profit(sell_price) / self.entry_price * SETTINGS.MULTIPLIER

    def hit_take_profit(self, high: float, low: float) -> bool:
        return high >= self.take_profit_price if self.is_long else low <= self.take_profit_price

    def take_profit_fill(self, open_price: float) -> float:
        """A resting limit order fills at the limit, or at the open when the bar gaps through it."""
        if self.is_long:
            return max(self.take_profit_price, open_price)

        return min(self.take_profit_price, open_price)

    def instrument_take_profit_price(self, instrument_acquired_price: float) -> float:
        """Limit price on the bought instrument that matches the underlying take-profit level at its leverage."""
        underlying_move = self.sign * (self.take_profit_price / self.entry_price - 1)

        return instrument_acquired_price * (1 + self.instrument_leverage * underlying_move)

    def confirm_stop_loss(self, close_price: float) -> bool:
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

    def _is_pullback(self, close_price: float) -> bool:
        profit = self.profit(close_price)
        self.max_profit = max(self.max_profit, profit)

        trigger_profit = SETTINGS.PULLBACK.TRIGGER_PROFIT * self.buy_price / SETTINGS.MULTIPLIER
        if self.max_profit <= trigger_profit:
            return False

        return profit < 0 or (self.max_profit - profit) / self.max_profit > SETTINGS.PULLBACK.VALUE
