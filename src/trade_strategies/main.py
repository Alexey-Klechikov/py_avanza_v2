import warnings
from datetime import datetime, time, timedelta
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
from services.ta import get_indicators, read_top_strategies
from services.ta.strategies.models import Strategy
from utils.constants import TODAY_MIDNIGHT
from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

log = get_logger()


class Signal(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    EXIT = "EXIT"


class Data:
    def __init__(self, settings):
        self.settings = settings
        self.data: pd.DataFrame = pd.DataFrame()
        self.is_new = False
        self.too_old = False
        self.strategies = []

    def get(self):
        storage = Storage(self.settings)

        data = storage.read()
        data_size_before = data.shape[0]

        if self.settings.TRADING_DATA == "avanza":
            new_data = Chart.get_chart_data(self.settings, TimePeriod.TODAY, Resolution.TWO_MINUTES)
        elif self.settings.TRADING_DATA == "yahoo":
            new_data = Ticker(self.settings).get_history(period=Period.ONE_DAY, interval=Interval.TWO_MINUTES)
        else:
            raise ValueError(f"Unknown data source {self.settings.TRADING_DATA}")

        storage.write(new_data)

        data = storage.read()
        data_size_after = data.shape[0]

        self.data = data.loc[data.index >= TODAY_MIDNIGHT - timedelta(days=4)]

        self.too_old = ((datetime.now() - self.data.index[-1]).seconds // 60) > 15
        self.is_new = data_size_before != data_size_after

    def get_strategies(self):
        indicators_mapping = get_indicators(self.data, self.settings)
        strategies = read_top_strategies(indicators_mapping)
        if not self.strategies or self.strategies[0].name != strategies[0].name:
            for i, strategy in enumerate(strategies):
                log.info(f"Strategy {i+1}: {strategy.name}")

        self.strategies = strategies

    def add_signals(self, strategy: Strategy) -> None:
        self.data["LONG"] = False
        self.data["SHORT"] = False
        self.data["EXIT"] = False

        for column in ["LONG", "SHORT", "EXIT"]:
            combination_condition = all if column in ["LONG", "SHORT"] else any

            signal_methods = [
                indicator.signal.__getattribute__(column)
                for indicator in strategy.indicators_logic  # type: ignore
                if indicator.signal.__getattribute__(column) is not None
            ]

            for i, row in self.data.iterrows():
                self.data.at[i, column] = (
                    False
                    if not signal_methods
                    or not combination_condition(signal_method(row) for signal_method in signal_methods)
                    else True
                )

        for column in ["LONG", "SHORT", "EXIT"]:
            for non_trading_time in (
                ["09:00", self.settings.TRADING_START.strftime("%H:%M")],
                [self.settings.TRADING_END.strftime("%H:%M"), "22:30"],
            ):
                self.data.loc[self.data.between_time(non_trading_time[0], non_trading_time[1]).index, column] = False

    def get_signal(self) -> Signal | None:
        signal = None

        for i, strategy in enumerate(self.strategies):
            self.add_signals(strategy)

            last_complete_candle = self.data.iloc[-2]
            if last_complete_candle["EXIT"]:
                signal = Signal.EXIT

            if last_complete_candle["LONG"] and not last_complete_candle["SHORT"]:
                signal = Signal.LONG

            elif last_complete_candle["SHORT"] and not last_complete_candle["LONG"]:
                signal = Signal.SHORT

            if not signal:
                continue

            log.info(f"Signal: {signal}. Strategy {i+1}. Latest price: {round(self.data.iloc[-1]['Close'], 2)}")
            return signal


class FlowAction(Enum):
    TRADE = "TRADE"
    DO_NOTHING = "DO_NOTHING"
    EXIT_TRADING = "EXIT_TRADING"


class Flow:
    def __init__(self, settings, dry_run=False):
        self.budget = settings.BUDGET
        self.trading_ends: time = min(get_market_close_time(), settings.TRADING_END)
        self.stop_loss: float = settings.TRADING_STOP_LOSS
        self.dry_run: bool = dry_run

        self.directions_sell: list[Direction] = []
        self.directions_buy: list[Direction] = []

    def get_action(self, data: Data, portfolio: Portfolio, orders: Orders) -> FlowAction:
        self.directions_sell = []
        self.directions_buy = []

        portfolio.reload_positions(caller="get_action")

        # Stop loss
        if portfolio.positions:
            for direction in [Direction.BULL, Direction.BEAR]:
                acquired_instrument = portfolio.acquired_instrument.get(direction.value)
                if not acquired_instrument:
                    continue

                if (
                    acquired_instrument
                    and acquired_instrument.quote.sell
                    and acquired_instrument.quote.sell < acquired_instrument.acquired_price * (1 - self.stop_loss)
                ):
                    log.info(f"Stop loss triggered for {direction.value}")
                    self.directions_sell = [direction]
                    return FlowAction.TRADE

        # Edge case: Sell BEAR at 14:24 if last signal was more than 90 mins ago
        if datetime.now().time() == time(14, 26) and portfolio.acquired_instrument.BEAR:
            orders.reload_active()
            if orders.active_order:
                if (datetime.now() - orders.active_order.created).total_seconds() > (90 * 60):
                    self.directions_sell = [Direction.BEAR]
                    return FlowAction.TRADE

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
        elif data.too_old:
            self.directions_sell = [Direction.BEAR, Direction.BULL]
            return FlowAction.TRADE

        # Trade
        elif data.is_new:
            data.is_new = False
            data.get_strategies()
            signal = data.get_signal()

            if signal:
                # Not enough funds on the account
                portfolio.reload_balance()
                if portfolio.buying_power < self.budget and not portfolio.positions:
                    log.info("Not enough funds on the account. No action is taken.")
                    return FlowAction.EXIT_TRADING

            if signal == Signal.LONG:
                self.directions_sell = [Direction.BEAR]
                self.directions_buy = [Direction.BULL]
            elif signal == Signal.SHORT:
                self.directions_sell = [Direction.BULL]
                self.directions_buy = [Direction.BEAR]
            elif signal == Signal.EXIT:
                self.directions_sell = [Direction.BEAR, Direction.BULL]

            if signal:
                return FlowAction.TRADE

        # Wait for new data
        sleep(120 - ((datetime.now().minute * 60 + datetime.now().second) % 120) + 6)
        data.get()

        if not data.is_new:
            sleep(20)
            data.get()
            log.warning(f"Data is not new, wait and refetch. 20 seconds later data is new: {data.is_new}")

        return FlowAction.DO_NOTHING


# MAIN
def trade(dry_run: bool, settings) -> None:
    log.info(
        f"Start trading strategies on {settings.NAME} | {settings.RESOLUTION}" + (" | DRY_RUN" if dry_run else ""),
    )

    data = Data(settings)
    data.get()

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

    flow = Flow(settings, dry_run)

    while datetime.now().time() < time(17, 4):
        try:
            action = flow.get_action(data, portfolio, orders)
        except (ConnectionError, RemoteDisconnected):
            get_client.cache_clear()

        if action == FlowAction.DO_NOTHING:
            continue
        elif action == FlowAction.EXIT_TRADING:
            break
        elif action == FlowAction.TRADE:
            pass

        for direction in flow.directions_sell:
            Trade.sell(direction, orders, portfolio, dry_run)

        for direction in flow.directions_buy:
            Trade.buy(direction, orders, watchlists, portfolio, settings.BUDGET, dry_run)
            Trade.take_profit(direction, orders, portfolio, settings.TRADING_TAKE_PROFIT)

    Transactions(settings.ACCOUNT_ID).log_deals(only_today=True)
