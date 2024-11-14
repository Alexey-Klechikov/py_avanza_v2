import warnings
from datetime import datetime, time
from enum import Enum
from http.client import RemoteDisconnected
from time import sleep

import pandas as pd
from avanza.constants import Resolution, TimePeriod
from requests.exceptions import ConnectionError

from apis.avanza.client import get_client
from apis.avanza.operators import Chart, Orders, Portfolio, Transactions, Watchlists
from apis.avanza.trade import Trade
from apis.avanza.trade.models import Direction
from apis.yahoo.client.models import Interval, Period
from apis.yahoo.operators import Ticker
from services import Storage
from services.calendar import get_market_close_time, get_market_is_close
from services.candlesticks.operators import append_talib_candlestick_patterns
from trade_candlesticks import BacklogTradeCandlesticks
from trade_candlesticks.models import CandlestickPatternRule
from utils.constants import TODAY_MIDNIGHT
from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

log = get_logger()


class Signal(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class Data:
    def __init__(self, settings, candlestick_rules: list[CandlestickPatternRule]):
        self.settings = settings
        self.candlestick_rules = candlestick_rules
        self.data = pd.DataFrame()
        self.is_new = False
        self.too_old = False
        self.triggered_pattern = None

    def get(self):
        storage = Storage(self.settings)

        data = storage.read()

        self.data = data.loc[data.index >= TODAY_MIDNIGHT]

        if ((datetime.now() - data.index[-1]).seconds) < 2 * 60:  # type: ignore
            self.too_old = False
            self.is_new = True

        else:
            if self.settings.TRADING_DATA == "avanza":
                new_data = Chart.get_chart_data(self.settings, TimePeriod.TODAY, Resolution.TWO_MINUTES)
            elif self.settings.TRADING_DATA == "yahoo":
                new_data = Ticker(self.settings).get_history(period=Period.ONE_DAY, interval=Interval.TWO_MINUTES)
            else:
                raise ValueError(f"Unknown data source {self.settings.TRADING_DATA}")

            storage.write(new_data)

            data_size_before = data.shape[0]
            data = storage.read()
            data_size_after = data.shape[0]

            self.too_old = ((datetime.now() - data.index[-1]).seconds // 60) > 15
            self.is_new = data_size_before != data_size_after

        self.data = data.loc[data.index >= TODAY_MIDNIGHT]

    def get_latest_triggered_rule(self) -> CandlestickPatternRule | None:
        self.data = append_talib_candlestick_patterns(self.data, list({i.column for i in self.candlestick_rules}))

        for i in range(len(self.data) - 1, len(self.data) - 3, -1):
            for candlestick_rule in self.candlestick_rules:
                if (self.data[candlestick_rule.column][i] == 100 and candlestick_rule.direction == Direction.BULL) or (
                    self.data[candlestick_rule.column][i] == -100 and candlestick_rule.direction == Direction.BEAR
                ):
                    return candlestick_rule


class FlowAction(Enum):
    TRADE = "TRADE"
    DO_NOTHING = "DO_NOTHING"
    EXIT_TRADING = "EXIT_TRADING"


class Flow:
    def __init__(self, settings, data: Data, dry_run: bool):
        self.budget = settings.BUDGET
        self.trading_ends = min(get_market_close_time(), settings.TRADING_END)

        self.directions_sell: list[Direction] = []
        self.directions_buy: list[Direction] = []

        self.trading_ends: time = min(get_market_close_time(), settings.TRADING_END)
        self.dry_run: bool = dry_run

        self.directions_sell: list[Direction] = []
        self.directions_buy: list[Direction] = []

        self.triggered_rule: CandlestickPatternRule | None = None

        self.data = data

    def get_action(self, portfolio: Portfolio, orders: Orders) -> FlowAction:
        self.directions_sell = []
        self.directions_buy = []
        latest_triggered_rule = None

        portfolio.reload_positions(caller="get_action")
        if not portfolio.positions:
            self.triggered_rule = None

        # End of day
        if datetime.now().time() >= self.trading_ends:
            # Edge case: Sell at the end of the day is last signal was more than 90 mins ago
            orders.reload_active()
            if (
                portfolio.positions
                and not get_market_is_close()
                and (
                    not orders.active_order or (datetime.now() - orders.active_order.created).total_seconds() > (90 * 60)
                )
            ):
                self.directions_sell = [Direction.BULL, Direction.BEAR]
                return FlowAction.TRADE

            return FlowAction.EXIT_TRADING

        # No new data
        elif self.data.too_old:
            self.directions_sell = [Direction.BEAR, Direction.BULL]
            return FlowAction.TRADE

        # Trade
        elif self.data.is_new:
            self.data.is_new = False
            latest_triggered_rule = self.data.get_latest_triggered_rule()

        if (
            latest_triggered_rule
            and latest_triggered_rule != self.triggered_rule
            and (not self.triggered_rule or latest_triggered_rule.efficiency > self.triggered_rule.efficiency)
        ):
            log.info(
                f"New signal: {Signal('LONG' if latest_triggered_rule.direction == Direction.BULL else 'SHORT')}. "
                + f"Pattern: {latest_triggered_rule.column} [eff. {latest_triggered_rule.efficiency}, "
                + f"SL {latest_triggered_rule.stop_loss}, TP {latest_triggered_rule.take_profit}]",
            )

            self.triggered_rule = latest_triggered_rule

            # Not enough funds on the account
            portfolio.reload_balance()
            if portfolio.buying_power < self.budget and not portfolio.positions:
                log.info("Not enough funds on the account. No action is taken.")
                return FlowAction.EXIT_TRADING

            if self.triggered_rule.direction == Direction.BULL:
                self.directions_sell = [Direction.BEAR]
                self.directions_buy = [Direction.BULL]
            elif self.triggered_rule.direction == Direction.BEAR:
                self.directions_sell = [Direction.BULL]
                self.directions_buy = [Direction.BEAR]

            return FlowAction.TRADE

        return FlowAction.DO_NOTHING

    def wait_for_data(self):
        sleep(120 - ((datetime.now().minute * 60 + datetime.now().second) % 120) + 16)
        self.data.get()

        if not self.data.is_new:
            sleep(20)
            self.data.get()
            log.warning(f"Data is not new, wait and refetch. 20 seconds later data is new: {self.data.is_new}")


# MAIN
def trade(dry_run: bool, settings) -> None:
    log.info(
        f"Start trading candlesticks on {settings.NAME} | {settings.RESOLUTION}" + (" | DRY_RUN" if dry_run else ""),
    )

    backlog = BacklogTradeCandlesticks()
    backlog.read_rules()

    data = Data(settings, backlog.rules)

    orders = Orders(
        account_id=settings.ACCOUNT_ID,
        filter_orderbook_name=settings.NAME,
        dry_run=dry_run,
    )

    portfolio = Portfolio(
        account_id=settings.ACCOUNT_ID,
        filter_orderbook_name=settings.NAME,
    )
    portfolio.reload_positions()
    portfolio.reload_balance()

    watchlists = Watchlists(settings)
    watchlists.update_all()

    trade = Trade(orders=orders, portfolio=portfolio, watchlists=watchlists, dry_run=dry_run, budget=settings.BUDGET)
    flow = Flow(settings, data, dry_run)

    while datetime.now().time() < time(17, 15):
        try:
            action = flow.get_action(portfolio, orders)
        except (ConnectionError, RemoteDisconnected):
            get_client.cache_clear()

        if action == FlowAction.DO_NOTHING:
            for direction in [Direction.BULL, Direction.BEAR]:
                trade.stop_loss(direction)

        elif action == FlowAction.TRADE:
            for direction in flow.directions_sell:
                trade.sell(direction)

            for direction in flow.directions_buy:
                trade.buy(direction)

                if not flow.triggered_rule:
                    continue

                trade.stop_loss_percent = flow.triggered_rule.stop_loss
                trade.take_profit_percent = flow.triggered_rule.take_profit

                trade.take_profit(direction)

        elif action == FlowAction.EXIT_TRADING:
            break

        flow.wait_for_data()

    Transactions(settings.ACCOUNT_ID).log_deals(only_today=True)
