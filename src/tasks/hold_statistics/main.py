import warnings
from datetime import datetime, time
from time import sleep

import pandas as pd

from apis.avanza.client import get_client
from apis.avanza.operators import Orders, Portfolio, Transactions, Watchlists
from apis.avanza.trade import Trade
from services.calendar import get_market_is_close
from tasks.hold_statistics import BacklogHoldStatistics
from tasks.hold_statistics.models import Action, Event
from utils.logger import get_logger

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
            break

        sleep_until_next_event(event)

        if get_market_is_close():
            break

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

        watchlists = Watchlists(event.settings, "CERTIFICATE")

        trade = Trade(
            orders=orders,
            portfolio=portfolio,
            watchlists=watchlists,
            dry_run=dry_run,
            budget_percent=settings.BUDGET,
        )

        if event.action == Action.SELL:
            trade.sell(event.orderbook_direction)

        if event.action == Action.BUY:
            log.info(f"Signal: Signal.{'LONG' if event.orderbook_direction.value == 'BULL' else 'SHORT'}")

            portfolio.reload_balance()

            if portfolio.buying_power < event.budget:
                log.warning(f"Insufficient buying power: {portfolio.buying_power} < {event.budget}")
                continue

            trade.buy(event.orderbook_direction)

            trade.take_profit_percent = event.take_profit

            trade.take_profit(event.orderbook_direction)

    Transactions(settings.ACCOUNT_ID).log_deals(only_today=True)
