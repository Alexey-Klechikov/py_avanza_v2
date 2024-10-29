import warnings

import pandas as pd
from avanza.constants import OrderType

from apis.avanza.operators import Orders, Portfolio, Watchlists
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
        trade_result = None
        for _ in range(5):
            orders.delete_all()

            portfolio.reload_positions(caller="sell")
            acquired_instrument = portfolio.acquired_instrument.get(direction.value)
            if not acquired_instrument:
                break

            orders.place(
                order_book_id=acquired_instrument.instrument.id,
                instrument_name=acquired_instrument.instrument.name,
                order_type=OrderType.SELL,
                price=acquired_instrument.quote.buy,
                volume=int(acquired_instrument.volume),
            )

            trade_result = (
                f"Trade result: {round(acquired_instrument.acquired_value)} -> {round(acquired_instrument.value)}"
            )

            if dry_run:
                break

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
        for _ in range(5):
            orders.delete_all()

            portfolio.reload_positions(caller="buy")
            acquired_instrument = portfolio.acquired_instrument.get(direction.value)
            if acquired_instrument:
                break

            watchlists.refresh_all()
            preferred_instrument = watchlists.preferred_instrument.get(direction.value)
            if not preferred_instrument or not preferred_instrument.sell:
                watchlists.update_all()
                continue

            orders.place(
                order_book_id=preferred_instrument.id,
                instrument_name=preferred_instrument.name,
                order_type=OrderType.BUY,
                price=preferred_instrument.sell,
                volume=round(budget // preferred_instrument.sell),
            )

            if dry_run:
                break

    @classmethod
    def take_profit(
        cls,
        direction: Direction,
        orders: Orders,
        portfolio: Portfolio,
        take_profit: float,
    ) -> None:
        orders.delete_all()

        portfolio.reload_positions(caller="take_profit")
        acquired_instrument = portfolio.acquired_instrument.get(direction.value)
        if not acquired_instrument or not acquired_instrument.quote.sell:
            return

        orders.place(
            order_book_id=acquired_instrument.instrument.id,
            instrument_name=acquired_instrument.instrument.name,
            order_type=OrderType.SELL,
            price=round(
                (acquired_instrument.quote.buy or acquired_instrument.acquired_price) * (1 + take_profit),
                2,
            ),
            volume=int(acquired_instrument.volume),
        )
