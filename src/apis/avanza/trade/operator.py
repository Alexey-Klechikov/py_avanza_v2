import warnings
from dataclasses import dataclass, field
from time import sleep

import pandas as pd
from avanza.constants import OrderType

from apis.avanza.operators import Instrument, Orders, Portfolio, Watchlists
from apis.avanza.trade.models import Direction
from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

log = get_logger()


@dataclass
class DirectionPrice:
    buy: float = 0
    volume: float = 0
    signal: float | None = None
    take_profit: float | None = None
    sell: float | None = None


@dataclass
class PriceState:
    BULL: DirectionPrice = field(default_factory=DirectionPrice)
    BEAR: DirectionPrice = field(default_factory=DirectionPrice)

    def update(
        self,
        direction: Direction,
        **kwargs,
    ) -> None:
        direction_price = getattr(self, direction.value)

        for key, value in kwargs.items():
            setattr(direction_price, key, value)

        setattr(self, direction.value, direction_price)

    def reset(self, direction: Direction) -> None:
        direction_price = getattr(self, direction.value)
        if direction_price.signal and (direction_price.sell or direction_price.take_profit):
            log.warning(
                f"Trade result: {round(direction_price.buy * direction_price.volume)} "
                f"-> {round((direction_price.sell or direction_price.take_profit) * direction_price.volume)} ",
            )

        setattr(self, direction.value, DirectionPrice())

    def set(
        self,
        direction: Direction,
        buy: float,
        volume: float,
    ) -> None:
        setattr(
            self,
            direction.value,
            DirectionPrice(
                signal=buy,
                buy=buy,
                volume=volume,
            ),
        )

    def get(self, direction: Direction) -> DirectionPrice:
        return getattr(self, direction.value)


class Trade:
    def __init__(
        self,
        orders: Orders,
        portfolio: Portfolio,
        watchlists: Watchlists,
        dry_run: bool,
        budget_percent: int,
        stop_loss_percent: float | None = None,
        take_profit_percent: float | None = None,
    ) -> None:
        self.orders = orders
        self.portfolio = portfolio
        self.watchlists = watchlists

        self.dry_run = dry_run

        self.budget_percent = budget_percent
        self.stop_loss_percent = stop_loss_percent
        self.take_profit_percent = take_profit_percent

        self.price_state: PriceState = PriceState()

    def sell(self, direction: Direction) -> None:
        caller = "sell"

        if self.dry_run:
            return

        for _ in range(5):
            self.portfolio.reload_positions(caller)
            acquired_instrument = self.portfolio.acquired_instrument.get(direction.value)
            if not acquired_instrument:
                self.price_state.reset(direction)
                break

            self.orders.delete_all(caller)
            self.orders.place(
                order_book_id=acquired_instrument.instrument.id,
                instrument_name=acquired_instrument.instrument.name,
                order_type=OrderType.SELL,
                price=acquired_instrument.quote.buy,
                volume=int(acquired_instrument.volume),
                caller=caller,
            )

            self.price_state.update(
                direction,
                buy=acquired_instrument.acquired_price,
                volume=acquired_instrument.volume,
                sell=acquired_instrument.quote.buy,
            )

    def buy(self, direction: Direction) -> None:
        caller = "buy"
        budget = None

        if self.dry_run:
            return

        for _ in range(5):
            self.portfolio.reload_positions(caller)
            acquired_instrument = self.portfolio.acquired_instrument.get(direction.value)
            if acquired_instrument:
                self.price_state.update(
                    direction,
                    buy=acquired_instrument.acquired_price,
                    volume=acquired_instrument.volume,
                    signal=acquired_instrument.quote.sell,
                )
                break

            elif self.price_state.get(direction).sell:
                self.price_state.reset(direction)

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
                budget = max(1200, round(self.portfolio.total_value * self.budget_percent))

                if self.portfolio.buying_power < budget:
                    log.warning(f"Buying power is not enough for budget {budget}")
                    return

            self.orders.delete_all(caller)
            self.orders.place(
                order_book_id=preferred_instrument.id,
                instrument_name=preferred_instrument.name,
                order_type=OrderType.BUY,
                price=price,
                volume=round(budget // price),
                caller=caller,
            )

    def take_profit(self, direction: Direction) -> None:
        caller = "take_profit"

        if not self.take_profit_percent:
            return

        for _ in range(5):
            self.portfolio.reload_positions(caller)
            acquired_instrument = self.portfolio.acquired_instrument.get(direction.value)
            if not acquired_instrument:
                self.price_state.reset(direction)
                break

            price = round(acquired_instrument.acquired_price * (1 + self.take_profit_percent), 2)

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

            self.price_state.update(
                direction,
                buy=acquired_instrument.acquired_price,
                volume=acquired_instrument.volume,
                take_profit=price,
            )

    def stop_loss(self, direction: Direction) -> None:
        caller = "stop_loss"

        if not self.stop_loss_percent:
            return

        for _ in range(5):
            self.portfolio.reload_positions(caller)
            acquired_instrument = self.portfolio.acquired_instrument.get(direction.value)
            if not acquired_instrument:
                self.price_state.reset(direction)
                break

            price = Instrument(
                acquired_instrument.instrument.id,
                acquired_instrument.instrument.type.name,
            ).get_buy_price()
            if not price:
                sleep(3)
                continue

            if price > (self.price_state.get(direction).signal or acquired_instrument.acquired_price) * (
                1 - self.stop_loss_percent
            ):
                return

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

            self.price_state.update(
                direction,
                buy=acquired_instrument.acquired_price,
                volume=acquired_instrument.volume,
                sell=price,
            )
