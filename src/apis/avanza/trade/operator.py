import warnings
from dataclasses import dataclass
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
class SignalPrice:
    BULL: float | None = None
    BEAR: float | None = None

    def update(self, direction: Direction, price: float | None) -> None:
        if price:
            setattr(self, direction.value, price)

    def reset(self, direction: Direction) -> None:
        setattr(self, direction.value, None)

    def get(self, direction: Direction) -> float | None:
        return getattr(self, direction.value)


class Trade:
    def __init__(
        self,
        orders: Orders,
        portfolio: Portfolio,
        watchlists: Watchlists,
        dry_run: bool,
        budget: int,
        stop_loss_percent: float | None = None,
        take_profit_percent: float | None = None,
    ) -> None:
        self.orders = orders
        self.portfolio = portfolio
        self.watchlists = watchlists

        self.dry_run = dry_run

        self.budget = budget
        self.stop_loss_percent = stop_loss_percent
        self.take_profit_percent = take_profit_percent

        self.signal_price: SignalPrice = SignalPrice()

    def sell(self, direction: Direction) -> None:
        caller = "sell"

        if self.dry_run:
            return

        trade_result = None
        for _ in range(5):
            self.portfolio.reload_positions(caller)
            acquired_instrument = self.portfolio.acquired_instrument.get(direction.value)
            if not acquired_instrument:
                self.signal_price.reset(direction)
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

            trade_result = (
                f"Trade result: {round(acquired_instrument.acquired_value)} -> {round(acquired_instrument.value)}"
            )

        if trade_result:
            log.warning(trade_result)

    def buy(self, direction: Direction) -> None:
        caller = "buy"

        if self.dry_run:
            return

        for _ in range(5):
            self.portfolio.reload_positions(caller)
            acquired_instrument = self.portfolio.acquired_instrument.get(direction.value)
            if acquired_instrument:
                self.signal_price.update(direction, acquired_instrument.quote.sell)
                break

            self.watchlists.refresh_all()
            preferred_instrument = self.watchlists.preferred_instrument.get(direction.value)
            if not preferred_instrument or not preferred_instrument.sell:
                self.watchlists.update_all()
                continue

            price = Instrument(preferred_instrument.id, preferred_instrument.type).get_sell_price()
            if not price:
                sleep(3)
                continue

            self.orders.delete_all(caller)
            self.orders.place(
                order_book_id=preferred_instrument.id,
                instrument_name=preferred_instrument.name,
                order_type=OrderType.BUY,
                price=price,
                volume=round(self.budget // price),
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
                self.signal_price.reset(direction)
                break

            price = Instrument(
                acquired_instrument.instrument.id,
                acquired_instrument.instrument.type.name,
            ).get_buy_price()
            if not price:
                sleep(3)
                continue

            self.orders.delete_all(caller)
            self.orders.place(
                order_book_id=acquired_instrument.instrument.id,
                instrument_name=acquired_instrument.instrument.name,
                order_type=OrderType.SELL,
                price=round(price * (1 + self.take_profit_percent), 2),
                volume=int(acquired_instrument.volume),
                caller=caller,
            )
            self.orders.reload_active()
            if self.orders.active_order:
                break

    def stop_loss(self, direction: Direction) -> None:
        caller = "stop_loss"

        if not self.stop_loss_percent:
            return

        for _ in range(5):
            self.portfolio.reload_positions(caller)
            acquired_instrument = self.portfolio.acquired_instrument.get(direction.value)
            if not acquired_instrument:
                self.signal_price.reset(direction)
                break

            price = Instrument(
                acquired_instrument.instrument.id,
                acquired_instrument.instrument.type.name,
            ).get_buy_price()
            if not price:
                sleep(3)
                continue

            if price > (self.signal_price.get(direction) or acquired_instrument.acquired_price) * (
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
            if self.orders.active_order:
                break
