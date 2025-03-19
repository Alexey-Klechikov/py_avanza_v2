import warnings
from dataclasses import dataclass, field
from time import sleep

import pandas as pd
from avanza.constants import OrderType

from apis.avanza.operators import Instrument, Orders, Portfolio, Watchlists
from apis.avanza.operators.models import Position
from apis.avanza.trade.models import Direction
from utils.logger import get_logger

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
        if direction_price.sell or direction_price.take_profit:
            value_buy = round(direction_price.buy * direction_price.volume)
            value_sell = round((direction_price.sell or direction_price.take_profit) * direction_price.volume)
            log.warning(f"Trade result: {value_buy} -> {value_sell} [{value_sell - value_buy}]")

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
            DirectionPrice(buy=buy, volume=volume),
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
        stop_loss_percent: float,
        stop_loss_confirmation_count_min: int,
        take_profit_percent: float,
        pullback_percent: float,
        pullback_confirmation_count_min: int,
    ) -> None:
        self.orders = orders
        self.portfolio = portfolio
        self.watchlists = watchlists

        self.dry_run = dry_run

        self.max_profit = 0

        self.budget_percent = budget_percent
        self.stop_loss_percent = stop_loss_percent
        self.stop_loss_confirmation_count_min = stop_loss_confirmation_count_min
        self.stop_loss_confirmation_count_active = 0
        self.take_profit_percent = take_profit_percent
        self.pullback_percent = pullback_percent
        self.pullback_confirmation_count_min = pullback_confirmation_count_min
        self.pullback_confirmation_count_active = 0

        self.price_state: PriceState = PriceState()

    def sell(self, direction: Direction | None) -> None:
        caller = "sell"

        if self.dry_run or not direction:
            return

        for _ in range(5):
            self.portfolio.reload_positions(caller)
            acquired_instrument = self.portfolio.acquired_instrument.get(direction.value)
            if not acquired_instrument:
                self.price_state.reset(direction)
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

    def buy(self, direction: Direction | None) -> None:
        caller = "buy"
        budget = None

        if self.dry_run or not direction:
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
                break

            else:
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

            self.max_profit = 0

            self.orders.delete_all(caller)
            self.orders.place(
                order_book_id=preferred_instrument.id,
                instrument_name=preferred_instrument.name,
                order_type=OrderType.BUY,
                price=price,
                volume=round(budget // price),
                caller=caller,
            )

    def take_profit(self, direction: Direction | None) -> None:
        caller = "take_profit"

        if self.dry_run or not self.take_profit_percent or not direction:
            return

        for _ in range(5):
            self.portfolio.reload_positions(caller)
            acquired_instrument = self.portfolio.acquired_instrument.get(direction.value)
            if not acquired_instrument:
                self.price_state.reset(direction)
                break

            price = round(acquired_instrument.acquired_price * (1 + self.take_profit_percent), 2)

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

    def _hit_stop_loss(self, price: float, acquired_instrument: Position) -> bool:
        if price > (acquired_instrument.acquired_price) * (1 - self.stop_loss_percent):
            self.stop_loss_confirmation_count_active = 0
            return False

        self.stop_loss_confirmation_count_active += 1
        if self.stop_loss_confirmation_count_active <= self.stop_loss_confirmation_count_min:
            log.warning(
                "Stop loss confirmation count: {} / {}. Latest instrument price: {}".format(
                    self.stop_loss_confirmation_count_active,
                    self.stop_loss_confirmation_count_min,
                    price,
                ),
            )
            return False

        return True

    def _hit_pullback(self, price: float, acquired_instrument: Position) -> bool:
        profit = (price - acquired_instrument.acquired_price) / acquired_instrument.acquired_price
        self.max_profit = max(self.max_profit, profit)

        if self.max_profit > 0.015 and profit < 0:
            pass
        elif self.max_profit > 0.015 and (self.max_profit - profit) / self.max_profit > self.pullback_percent:
            pass
        else:
            self.pullback_confirmation_count_active = 0
            return False

        self.pullback_confirmation_count_active += 1
        if self.pullback_confirmation_count_active <= self.pullback_confirmation_count_min:
            log.warning(
                "Pullback confirmation count: {} / {}. Latest instrument price: {}".format(
                    self.pullback_confirmation_count_active,
                    self.pullback_confirmation_count_min,
                    price,
                ),
            )
            return False

        return True

    def stop_loss(self, direction: Direction | None) -> None:
        caller = "stop_loss"

        if self.dry_run or not self.stop_loss_percent or not direction:
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

            if not self._hit_stop_loss(price, acquired_instrument) and not self._hit_pullback(price, acquired_instrument):
                return

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
