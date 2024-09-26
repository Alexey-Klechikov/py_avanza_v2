import platform
import warnings
from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum
from time import sleep

import pandas as pd
from avanza.constants import OrderType

from apis.avanza.client import get_client
from apis.avanza.operators import Orders, Portfolio, Watchlists
from apis.telegram.operators import Telegram as TelegramBase
from config import SETTINGS_HOLD_OMX, HoldOMX
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

set_handlers("hold")
log = get_logger()


class Direction(Enum):
    BULL = "BULL"
    BEAR = "BEAR"


class Action(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Event:
    at: time
    orderbook_direction: Direction
    action: Action
    settings: HoldOMX
    take_profit: float
    budget: int


class Plan:
    def __init__(self):
        self.events = []
        self.event = None

    def add_events_using_settings(self, settings) -> None:
        for rule in settings.RULES:
            self.events.append(
                Event(
                    at=rule.buy_time,
                    action=Action.BUY,
                    orderbook_direction=Direction[rule.orderbook_direction],
                    take_profit=rule.take_profit,
                    budget=rule.budget,
                    settings=settings,
                ),
            )
            self.events.append(
                Event(
                    at=rule.sell_time,
                    action=Action.SELL,
                    orderbook_direction=Direction[rule.orderbook_direction],
                    take_profit=rule.take_profit,
                    budget=rule.budget,
                    settings=settings,
                ),
            )

        events = {}
        for event in self.events:
            key = (event.at, event.orderbook_direction)
            if key in events:
                if events[key].action == Action.BUY:
                    continue
            events[key] = event

        self.events = sorted(events.values(), key=lambda x: x.action.value, reverse=True)
        self.events = sorted(self.events, key=lambda x: x.at)

    def pop_next_event(self) -> None:
        while self.events:
            self.event = self.events.pop(0)
            if self.event.at < datetime.now().time():
                continue

            log.info(
                "Next event: {} {} {} at {}".format(
                    self.event.action.value,
                    self.event.orderbook_direction.value,
                    self.event.settings.NAME,
                    self.event.at.strftime("%H:%M"),
                ),
            )

            return

        self.event = None

    def sleep_until_next_event(self) -> None:
        if self.event is None:
            return

        sleep_time = (datetime.combine(datetime.today(), self.event.at) - datetime.now()).seconds
        hours, remainder = divmod(sleep_time, 3600)
        minutes, _ = divmod(remainder, 60)

        if sleep_time <= 0:
            return

        log.info(f"Sleeping for {hours} hours and {minutes} minutes")

        sleep(sleep_time)


class Trade:
    @classmethod
    def sell(
        cls,
        event: Event,
        orders: Orders,
        portfolio: Portfolio,
        dry_run: bool,
    ) -> None:
        if event.action != Action.SELL:
            return

        if not portfolio.positions:
            log.info("No positions to sell")
            return

        instrument_to_sell = getattr(portfolio.acquired_instrument, event.orderbook_direction.value)

        while True:
            orders.place(
                order_book_id=instrument_to_sell.instrument.id,
                instrument_name=instrument_to_sell.instrument.name,
                order_type=OrderType.SELL,
                price=instrument_to_sell.quote.buy,
                volume=int(instrument_to_sell.volume),
            )

            if dry_run:
                break

            if orders.active_order:
                orders.delete(order_id=orders.active_order.order_id)

            portfolio.reload_positions()
            if not portfolio.positions:
                break

    @classmethod
    def buy(
        cls,
        event: Event,
        orders: Orders,
        portfolio: Portfolio,
        dry_run: bool,
    ) -> None:
        if event.action != Action.BUY:
            return

        if portfolio.positions:
            log.warning(
                "Already holding position(s): {}".format(" | ".join([i.instrument.name for i in portfolio.positions])),
            )

            position = portfolio.positions[0]

            orders.place(
                order_book_id=position.instrument.id,
                instrument_name=position.instrument.name,
                order_type=OrderType.SELL,
                price=round(
                    (position.quote.buy if position.quote.buy else position.acquired_price) * (1 + event.take_profit),
                    2,
                ),
                volume=int(position.volume),
            )

        else:
            while True:
                watchlist = Watchlists(event.settings)
                watchlist.refresh_watchlists(filter_orderbook_type="CERTIFICATE")

                instrument_to_buy = getattr(watchlist.preferred_instrument, event.orderbook_direction.value)
                volume = event.budget // instrument_to_buy.sell

                orders.place(
                    order_book_id=instrument_to_buy.id,
                    instrument_name=instrument_to_buy.name,
                    order_type=OrderType.BUY,
                    price=instrument_to_buy.sell,
                    volume=volume,
                )

                if dry_run:
                    break

                if orders.active_order:
                    orders.delete(order_id=orders.active_order.order_id)

                portfolio.reload_positions()
                if portfolio.positions:
                    break

            orders.place(
                order_book_id=instrument_to_buy.id,
                instrument_name=instrument_to_buy.name,
                order_type=OrderType.SELL,
                price=round(instrument_to_buy.sell * (1 + event.take_profit), 2),
                volume=volume,
            )


def hold(dry_run: bool, list_of_settings: list) -> None:
    log.info("Start holding" + (" | DRY_RUN" if dry_run else ""))

    plan = Plan()
    for i in list_of_settings:
        plan.add_events_using_settings(i)

    while datetime.now().time() < time(22, 10):
        plan.pop_next_event()
        if plan.event is None:
            return

        plan.sleep_until_next_event()

        get_client.cache_clear()

        orders = Orders(
            account_id=plan.event.settings.ACCOUNT_ID,
            filter_orderbook_name=plan.event.settings.NAME,
            filter_orderbook_direction=plan.event.orderbook_direction.value,
            filter_side=plan.event.action.value,
        )
        orders.reload_active()
        if orders.active_order:
            orders.delete(orders.active_order.order_id)

        portfolio = Portfolio(
            account_id=plan.event.settings.ACCOUNT_ID,
            filter_orderbook_name=plan.event.settings.NAME,
            filter_orderbook_direction=plan.event.orderbook_direction.value,
        )
        portfolio.reload_positions()
        portfolio.detect_acquired_instruments()

        Trade.sell(plan.event, orders, portfolio, dry_run)
        Trade.buy(plan.event, orders, portfolio, dry_run)


if __name__ == "__main__":
    try:
        dry_run = platform.system() == "Darwin"

        hold(dry_run, [SETTINGS_HOLD_OMX])

    except Exception as e:
        log.exception(str(e))

        telegram = TelegramBase()
        telegram.messages = ["Error in task_hold.py"]
        telegram.send_message()

        raise e
