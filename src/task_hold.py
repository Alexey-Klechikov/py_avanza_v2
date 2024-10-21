import platform
import warnings
from datetime import datetime, time
from time import sleep

import pandas as pd
from avanza.constants import OrderType

from apis.avanza.client import get_client
from apis.avanza.operators import Orders, Portfolio, Watchlists
from apis.telegram.operators import Telegram as TelegramBase
from config import SETTINGS_HOLD_OMX_MAIN
from services import BacklogHoldStatistics
from services.hold_statistics.models import Action, Event
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

set_handlers("hold")
log = get_logger()


class Trade:
    @classmethod
    def sell(
        cls,
        event: Event,
        orders: Orders,
        portfolio: Portfolio,
        dry_run: bool,
    ) -> None:
        trade_result = None
        for _ in range(5):
            orders.delete_all()

            portfolio.reload_positions(caller="sell")
            acquired_instrument = portfolio.acquired_instrument.get(event.orderbook_direction.value)
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
                return

        if trade_result:
            log.warning(trade_result)

    @classmethod
    def buy(
        cls,
        event: Event,
        orders: Orders,
        portfolio: Portfolio,
        dry_run: bool,
    ) -> None:
        for _ in range(5):
            orders.delete_all()

            portfolio.reload_positions(caller="buy")
            acquired_instrument = portfolio.acquired_instrument.get(event.orderbook_direction.value)
            if acquired_instrument:
                break

            watchlists = Watchlists(event.settings)
            watchlists.refresh_all(filter_orderbook_type="CERTIFICATE")
            preferred_instrument = watchlists.preferred_instrument.get(event.orderbook_direction.value)
            if not preferred_instrument:
                raise ValueError("No preferred instrument found")
            if not preferred_instrument.sell:
                log.warning("No sell price for %s", preferred_instrument.name)
                continue

            orders.place(
                order_book_id=preferred_instrument.id,
                instrument_name=preferred_instrument.name,
                order_type=OrderType.BUY,
                price=preferred_instrument.sell,
                volume=round(event.budget // preferred_instrument.sell),
            )

            if dry_run:
                break

    @classmethod
    def take_profit(cls, event: Event, orders: Orders, portfolio: Portfolio) -> None:
        orders.delete_all()

        portfolio.reload_positions(caller="take_profit")
        acquired_instrument = portfolio.acquired_instrument.get(event.orderbook_direction.value)
        if acquired_instrument:
            orders.place(
                order_book_id=acquired_instrument.instrument.id,
                instrument_name=acquired_instrument.instrument.name,
                order_type=OrderType.SELL,
                price=round(
                    (acquired_instrument.quote.buy or acquired_instrument.acquired_price) * (1 + event.take_profit),
                    2,
                ),
                volume=int(acquired_instrument.volume),
            )


def sleep_until_next_event(event: Event) -> None:
    if event is None:
        return

    sleep_time = (datetime.combine(datetime.today(), event.at) - datetime.now()).seconds
    hours, remainder = divmod(sleep_time, 3600)
    minutes, remainder = divmod(remainder, 60)

    if (datetime.now() - datetime.combine(datetime.today(), event.at)).seconds < 120:
        return

    log.info(f"Sleeping for {hours}:{minutes}:{remainder}")

    sleep(sleep_time)

    get_client.cache_clear()


# MAIN
def hold(dry_run: bool, list_of_settings: list) -> None:
    log.info("Start holding" + (" | DRY_RUN" if dry_run else ""))

    backlog = BacklogHoldStatistics()
    for settings in list_of_settings:
        backlog.read_rules(settings)
    backlog.extract_events_from_rules()

    while datetime.now().time() < time(18, 0):
        event = backlog.pop_next_event()
        if event is None:
            return

        sleep_until_next_event(event)

        orders = Orders(
            account_id=event.settings.ACCOUNT_ID,
            filter_orderbook_name=event.settings.NAME,
            filter_orderbook_direction=event.orderbook_direction.value,
        )

        portfolio = Portfolio(
            account_id=event.settings.ACCOUNT_ID,
            filter_orderbook_name=event.settings.NAME,
            filter_orderbook_direction=event.orderbook_direction.value,
        )

        if event.action == Action.SELL:
            Trade.sell(event, orders, portfolio, dry_run)

        if event.action == Action.BUY:
            portfolio.reload_balance()

            if portfolio.buying_power < event.budget:
                log.warning(f"Insufficient buying power: {portfolio.buying_power} < {event.budget}")
                continue

            Trade.buy(event, orders, portfolio, dry_run)
            Trade.take_profit(event, orders, portfolio)


if __name__ == "__main__":
    try:
        dry_run = platform.system() == "Darwin"

        hold(dry_run, [SETTINGS_HOLD_OMX_MAIN])

    except Exception as e:
        log.exception(str(e))

        telegram = TelegramBase()
        telegram.messages = ["Error in task_hold.py"]
        telegram.send_message()

        raise e
