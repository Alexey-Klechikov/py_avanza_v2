import warnings
from dataclasses import dataclass, field
from datetime import datetime
from time import sleep

import pandas as pd
from avanza.constants import OrderType

from apis.avanza.operators.instrument import Instrument
from apis.avanza.operators.orders import Orders
from apis.avanza.operators.portfolio import Portfolio
from apis.avanza.operators.watchlists import Watchlists
from config import DRY_RUN, SETTINGS
from services.trading.tracked_position import ExitLevels, TrackedPosition
from tasks.trade.models import Direction
from utils.logger.operators import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

log = get_logger()


@dataclass
class DirectionPrice:
    buy: float = 0
    volume: float = 0
    take_profit: float | None = None
    sell: float | None = None


@dataclass
class PriceState:
    BULL: DirectionPrice = field(default_factory=DirectionPrice)
    BEAR: DirectionPrice = field(default_factory=DirectionPrice)

    def update(self, direction: Direction, **kwargs) -> None:
        direction_price = getattr(self, direction.value)

        for key, value in kwargs.items():
            setattr(direction_price, key, value)

        setattr(self, direction.value, direction_price)

    def reset(self, direction: Direction) -> None:
        direction_price = getattr(self, direction.value)
        if direction_price.sell or direction_price.take_profit:
            value_buy = round(direction_price.buy * direction_price.volume)
            value_sell = round((direction_price.sell or direction_price.take_profit) * direction_price.volume)
            log.warning(f"Trade result: {value_buy} -> {value_sell} [{value_sell - value_buy}]")

        setattr(self, direction.value, DirectionPrice())

    def set(self, direction: Direction, buy: float, volume: float) -> None:
        setattr(self, direction.value, DirectionPrice(buy=buy, volume=volume))

    def get(self, direction: Direction) -> DirectionPrice:
        return getattr(self, direction.value)


class Trade:
    def __init__(self, orders: Orders, portfolio: Portfolio, watchlists: Watchlists, levels: ExitLevels) -> None:
        self.orders = orders
        self.portfolio = portfolio
        self.watchlists = watchlists
        self.levels = levels

        # Exit levels per held direction, on the underlying, exactly as the backtest tracks them
        self.tracked_positions: dict[Direction, TrackedPosition] = {}
        self.last_exit_check_bar: datetime | None = None

        self.price_state: PriceState = PriceState()

    def _track_new_position(self, direction: Direction, underlying_price: float, instrument_leverage: float) -> None:
        self.tracked_positions[direction] = TrackedPosition.open(
            is_long=direction == Direction.BULL,
            entry_price=underlying_price,
            instrument_leverage=instrument_leverage,
            levels=self.levels,
        )

    def _tracked_position(self, direction: Direction, underlying_price: float) -> TrackedPosition:
        """A held position without a record (restart, manual buy) is tracked from the current underlying price."""
        if direction not in self.tracked_positions:
            self._track_new_position(direction, underlying_price, instrument_leverage=SETTINGS.MULTIPLIER)

        return self.tracked_positions[direction]

    def _forget_position(self, direction: Direction) -> None:
        self.tracked_positions.pop(direction, None)
        self.price_state.reset(direction)

    def sell(self, direction: Direction | None) -> None:
        caller = "sell"

        if DRY_RUN or not direction:
            return

        for _ in range(5):
            self.portfolio.reload_positions(caller)
            acquired_instrument = self.portfolio.acquired_instrument.get(direction.value)
            if not acquired_instrument:
                self._forget_position(direction)
                break

            self.price_state.update(
                direction,
                buy=acquired_instrument.acquired_price,
                volume=acquired_instrument.volume,
                sell=acquired_instrument.quote.buy,
            )

            self.orders.delete_all(caller)
            self.orders.place(
                order_book_id=acquired_instrument.instrument.id,
                instrument_name=acquired_instrument.instrument.name,
                order_type=OrderType.SELL,
                price=acquired_instrument.quote.buy,
                volume=int(acquired_instrument.volume),
                caller=caller,
            )

    def buy(self, direction: Direction | None, underlying_price: float) -> None:
        caller = "buy"
        budget = None

        if DRY_RUN or not direction:
            return

        for _ in range(5):
            self.portfolio.reload_positions(caller)
            acquired_instrument = self.portfolio.acquired_instrument.get(direction.value)
            if acquired_instrument:
                self.price_state.update(
                    direction,
                    buy=acquired_instrument.acquired_price,
                    volume=acquired_instrument.volume,
                )
                self._tracked_position(direction, underlying_price)
                break

            else:
                self._forget_position(direction)

            self.watchlists.refresh_all()
            preferred_instrument = self.watchlists.preferred_instrument.get(direction.value)
            if not preferred_instrument or not preferred_instrument.sell:
                self.watchlists.update_all()
                continue

            price = Instrument(preferred_instrument.id, preferred_instrument.type).get_sell_price()
            if not price:
                sleep(3)
                continue

            if not budget:
                self.portfolio.reload_balance()
                budget = max(1200, round(self.portfolio.total_value * SETTINGS.BUDGET))

                if self.portfolio.buying_power + 1 < budget:
                    log.warning(f"Buying power is not enough for budget {budget}")
                    return

            self._track_new_position(direction, underlying_price, instrument_leverage=preferred_instrument.leverage)

            self.orders.delete_all(caller)
            self.orders.place(
                order_book_id=preferred_instrument.id,
                instrument_name=preferred_instrument.name,
                order_type=OrderType.BUY,
                price=price,
                volume=round(budget // price),
                caller=caller,
            )

    def take_profit(self, direction: Direction | None, underlying_price: float) -> None:
        caller = "take_profit"

        if DRY_RUN or not direction:
            return

        for _ in range(5):
            self.portfolio.reload_positions(caller)
            acquired_instrument = self.portfolio.acquired_instrument.get(direction.value)
            if not acquired_instrument:
                # The buy may not have filled yet: keep the position record buy() just created
                self.price_state.reset(direction)
                break

            tracked_position = self._tracked_position(direction, underlying_price)
            limit_price = tracked_position.instrument_take_profit_price(acquired_instrument.acquired_price)
            if limit_price is None:
                break  # no take-profit level: no resting order

            price = round(limit_price, 2)

            self.price_state.update(
                direction,
                buy=acquired_instrument.acquired_price,
                volume=acquired_instrument.volume,
                take_profit=price,
            )

            self.orders.reload_active()
            if self.orders.active_order and self.orders.active_order.price == price:
                break

            self.orders.delete_all(caller)
            self.orders.place(
                order_book_id=acquired_instrument.instrument.id,
                instrument_name=acquired_instrument.instrument.name,
                order_type=OrderType.SELL,
                price=price,
                volume=int(acquired_instrument.volume),
                caller=caller,
            )

    def stop_loss(self, direction: Direction | None, underlying_price: float, bar_time: datetime) -> None:
        caller = "stop_loss"

        # Confirmations count completed bars, as in the backtest, not loop iterations
        if DRY_RUN or not direction or bar_time == self.last_exit_check_bar:
            return

        self.portfolio.reload_positions(caller)
        if not self.portfolio.acquired_instrument.get(direction.value):
            self._forget_position(direction)
            return

        # Mark the bar checked only once positions loaded: a connection error must not skip a bar's confirmation
        self.last_exit_check_bar = bar_time
        tracked_position = self._tracked_position(direction, underlying_price)
        # Same order as the backtest: stop loss, then pullback, then the holding time
        exit_reason = None
        if tracked_position.confirm_stop_loss(underlying_price):
            exit_reason = "Stop loss"
        elif tracked_position.confirm_pullback(underlying_price):
            exit_reason = "Pullback"
        elif tracked_position.confirm_hold_expiry():
            exit_reason = "Holding time"

        if exit_reason is None:
            log.debug(
                "Underlying {} | stop loss {} ({} confirmations) | pullback confirmations {} | bars held {}/{}".format(
                    underlying_price,
                    tracked_position.stop_loss_price and round(tracked_position.stop_loss_price, 2),
                    tracked_position.stop_loss_confirmations,
                    tracked_position.pullback_confirmations,
                    tracked_position.bars_held,
                    tracked_position.hold_bars,
                ),
            )
            return

        log.info(f"{exit_reason} confirmed. Underlying price: {underlying_price}")

        for _ in range(5):
            self.portfolio.reload_positions(caller)
            acquired_instrument = self.portfolio.acquired_instrument.get(direction.value)
            if not acquired_instrument:
                self._forget_position(direction)
                break

            price = Instrument(
                acquired_instrument.instrument.id,
                acquired_instrument.instrument.type.name,
            ).get_buy_price()
            if not price:
                sleep(3)
                continue

            self.price_state.update(
                direction,
                buy=acquired_instrument.acquired_price,
                volume=acquired_instrument.volume,
                sell=price,
            )

            self.orders.delete_all(caller)
            self.orders.place(
                order_book_id=acquired_instrument.instrument.id,
                instrument_name=acquired_instrument.instrument.name,
                order_type=OrderType.SELL,
                price=price,
                volume=int(acquired_instrument.volume),
                caller=caller,
            )
            self.orders.reload_active()
