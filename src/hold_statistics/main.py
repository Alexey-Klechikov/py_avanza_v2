import warnings
from datetime import datetime, time
from time import sleep

import pandas as pd

from apis.avanza.client import get_client
from apis.avanza.operators import Orders, Portfolio, Transactions, Watchlists
from apis.avanza.trade import Trade
from hold_statistics import BacklogHoldStatistics
from hold_statistics.models import Action, Event
from utils.logger import add_extra_file_handler, get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

log = get_logger()


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
def hold(dry_run: bool, settings) -> None:
    log.info("Start holding" + (" | DRY_RUN" if dry_run else ""))

    backlog = BacklogHoldStatistics()
    backlog.read_rules(settings)
    backlog.extract_events_from_rules()

    while datetime.now().time() < time(17, 20):
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
            portfolio.reload_positions(caller="hold")

            if not portfolio.acquired_instrument.get(event.orderbook_direction.value):
                log.warning("No positions to sell. Possibly sold at take profit price")
                continue

            Trade.sell(event.orderbook_direction, orders, portfolio, dry_run)

        if event.action == Action.BUY:
            portfolio.reload_balance()

            if portfolio.buying_power < event.budget:
                log.warning(f"Insufficient buying power: {portfolio.buying_power} < {event.budget}")
                continue

            watchlists = Watchlists(event.settings, "CERTIFICATE")

            Trade.buy(event.orderbook_direction, orders, watchlists, portfolio, event.budget, dry_run)
            Trade.take_profit(event.orderbook_direction, orders, portfolio, event.take_profit)

    add_extra_file_handler("deals")
    Transactions(account_id=settings.ACCOUNT_ID).log_deals(log_header="hold_statistics")
