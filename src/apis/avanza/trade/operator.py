import warnings
from time import sleep

import pandas as pd
from avanza.constants import OrderType

from apis.avanza.operators import Instrument, Orders, Portfolio, Watchlists
from apis.avanza.trade.models import Direction
from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

log = get_logger()


class Trade:
    @classmethod
    def sell(
        cls,
        direction: Direction,
        orders: Orders,
        portfolio: Portfolio,
        dry_run: bool,
    ) -> None:
        caller = "sell"

        if dry_run:
            return

        trade_result = None
        for _ in range(5):
            portfolio.reload_positions(caller)
            acquired_instrument = portfolio.acquired_instrument.get(direction.value)
            if not acquired_instrument:
                break

            orders.delete_all(caller)
            orders.place(
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

    @classmethod
    def buy(
        cls,
        direction: Direction,
        orders: Orders,
        watchlists: Watchlists,
        portfolio: Portfolio,
        budget: int,
        dry_run: bool,
    ) -> None:
        caller = "buy"

        if dry_run:
            return

        for _ in range(5):
            portfolio.reload_positions(caller)
            acquired_instrument = portfolio.acquired_instrument.get(direction.value)
            if acquired_instrument:
                break

            watchlists.refresh_all()
            preferred_instrument = watchlists.preferred_instrument.get(direction.value)
            if not preferred_instrument or not preferred_instrument.sell:
                watchlists.update_all()
                continue

            price = Instrument(preferred_instrument.id, preferred_instrument.type).get_sell_price()
            if not price:
                sleep(3)
                continue

            orders.delete_all(caller)
            orders.place(
                order_book_id=preferred_instrument.id,
                instrument_name=preferred_instrument.name,
                order_type=OrderType.BUY,
                price=price,
                volume=round(budget // price),
                caller=caller,
            )

    @classmethod
    def take_profit(
        cls,
        direction: Direction,
        orders: Orders,
        portfolio: Portfolio,
        take_profit: float,
    ) -> None:
        caller = "take_profit"

        for _ in range(5):
            portfolio.reload_positions(caller)
            acquired_instrument = portfolio.acquired_instrument.get(direction.value)
            if not acquired_instrument:
                break

            price = Instrument(
                acquired_instrument.instrument.id,
                acquired_instrument.instrument.type.name,
            ).get_buy_price()
            if not price:
                sleep(3)
                continue

            orders.delete_all(caller)
            orders.place(
                order_book_id=acquired_instrument.instrument.id,
                instrument_name=acquired_instrument.instrument.name,
                order_type=OrderType.SELL,
                price=round(price * (1 + take_profit), 2),
                volume=int(acquired_instrument.volume),
                caller=caller,
            )
            orders.reload_active()
            if orders.active_order:
                break
