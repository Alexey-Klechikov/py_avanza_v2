import warnings
from datetime import datetime, timedelta
from enum import Enum
from http.client import RemoteDisconnected
from time import sleep

import pandas as pd
from avanza.constants import Resolution, TimePeriod

from apis.avanza.client.client import get_client
from apis.avanza.operators.chart import Chart
from apis.avanza.operators.orders import Orders
from apis.avanza.operators.portfolio import Portfolio
from apis.avanza.operators.transactions import Transactions
from apis.avanza.operators.watchlists import Watchlists
from apis.avanza.trade.models.direction import Direction
from apis.avanza.trade.operator import Trade
from apis.yahoo.client.models.history_request import Interval, Period
from apis.yahoo.operators.ticker import Ticker
from config import SETTINGS
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
    def __init__(self):
        self.data: pd.DataFrame = pd.DataFrame()
        self.is_new = False
        self.too_old = False
        self.strategies = []

    def get(self):
        storage = Storage()

        data = storage.read()

        if ((datetime.now() - data.index[-1]).seconds) < 2 * 60:  # type: ignore
            self.too_old = False
            self.is_new = True

        else:
            new_data = None
            if SETTINGS.DATA_SOURCE == "yahoo":
                try:
                    new_data = Ticker().get_history(period=Period.ONE_DAY, interval=Interval.TWO_MINUTES)
                except Exception as e:
                    log.warning(f"Error fetching Yahoo data: {e}. Will use avanza data instead.")
                    SETTINGS.DATA_SOURCE = "avanza"

            if SETTINGS.DATA_SOURCE == "avanza":
                new_data = Chart.get_chart_data(TimePeriod.TODAY, Resolution.TWO_MINUTES)

            if new_data is None:
                raise ValueError("No data fetched")

            storage.write(new_data)

            data_size_before = data.shape[0]
            data = storage.read()
            data_size_after = data.shape[0]

            self.too_old = ((datetime.now() - data.index[-1]).seconds // 60) > 15
            self.is_new = data_size_before != data_size_after

        self.data = data.loc[data.index >= TODAY_MIDNIGHT - timedelta(days=4)]

    def get_strategies(self):
        indicators_mapping = get_indicators(self.data)
        strategies = read_top_strategies(
            indicators_mapping,
            SETTINGS.NAME,
            filter_by_min_efficiency=SETTINGS.STRATEGY.MIN_EFFICIENCY,
            limit_count=SETTINGS.STRATEGY.COUNT_MAX,
        )
        if not self.strategies or self.strategies[0].name != strategies[0].name:
            for i, strategy in enumerate(strategies):
                log.info(f"Strategy {i+1} [{strategy.efficiency}]: {strategy.name}")

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
                ["09:00", SETTINGS.TIME.START.strftime("%H:%M")],
                [SETTINGS.TIME.END.strftime("%H:%M"), "22:30"],
            ):
                self.data.loc[self.data.between_time(non_trading_time[0], non_trading_time[1]).index, column] = False

    def get_signal(self, last_triggered_strategy: Strategy | None) -> tuple[Strategy | None, Signal | None]:
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

            message_signal_summary = (
                f"Signal: {signal}. Strategy {i+1} [{strategy.efficiency}]. "
                + f"Latest price: {round(self.data.iloc[-1]['Close'], 2)}"
            )
            if last_triggered_strategy and strategy.efficiency < last_triggered_strategy.efficiency:
                log.debug(f"[IGNORED] {message_signal_summary}")
                signal = None
                break

            log.info(message_signal_summary)
            return (strategy, signal)

        return (last_triggered_strategy, signal)


class FlowAction(Enum):
    TRADE = "TRADE"
    DO_NOTHING = "DO_NOTHING"
    EXIT_TRADING = "EXIT_TRADING"


class Flow:
    def __init__(self, data: Data):
        self.directions_sell: list[Direction] = []
        self.direction_buy: Direction | None = None
        self.direction_in_stock: Direction | None = None

        self.data = data

        self.triggered_strategy: Strategy | None = None

    def get_action(self, portfolio: Portfolio, orders: Orders) -> FlowAction:
        self.directions_sell = []
        self.direction_buy = None

        portfolio.reload_positions(caller="get_action")
        if not portfolio.positions:
            self.triggered_strategy = None

        # Start of the day
        if datetime.now().time() <= SETTINGS.TIME.START:
            if orders.active_order or not portfolio.positions:
                return FlowAction.DO_NOTHING

            for direction in [Direction.BULL, Direction.BEAR]:
                if not portfolio.acquired_instrument.get(direction.value):
                    continue

                self.direction_buy = direction
                return FlowAction.TRADE

        # End of day
        if datetime.now().time() >= min(get_market_close_time(), SETTINGS.TIME.END):
            orders.reload_active()
            if portfolio.positions and not get_market_is_close():
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
            self.data.get_strategies()
            self.triggered_strategy, signal = self.data.get_signal(self.triggered_strategy)

            if signal:
                # Not enough funds on the account
                portfolio.reload_balance()
                if portfolio.buying_power < 1100 and not portfolio.positions:
                    log.info("Not enough funds on the account. No action is taken.")
                    return FlowAction.EXIT_TRADING

            if signal == Signal.LONG:
                self.directions_sell = [Direction.BEAR]
                self.direction_buy = Direction.BULL
            elif signal == Signal.SHORT:
                self.directions_sell = [Direction.BULL]
                self.direction_buy = Direction.BEAR
            elif signal == Signal.EXIT:
                self.directions_sell = [Direction.BEAR, Direction.BULL]

            if signal:
                return FlowAction.TRADE

        return FlowAction.DO_NOTHING

    def wait_for_data(self):
        sleep(120 - ((datetime.now().minute * 60 + datetime.now().second) % 120) + 6)
        self.data.get()

        if not self.data.is_new:
            sleep(20)
            self.data.get()
            log.debug(f"Data is not new, wait and refetch. 20 seconds later data is new: {self.data.is_new}")


# MAIN
def trade() -> None:
    log.info(
        "Start trading strategies on {} | {}{}".format(
            SETTINGS.NAME,
            SETTINGS.RESOLUTION,
            " | DRY_RUN" if SETTINGS.DRY_RUN else "",
        ),
    )

    data = Data()

    orders = Orders()
    orders.reload_active()

    portfolio = Portfolio()
    portfolio.reload_positions()
    portfolio.reload_balance()

    watchlists = Watchlists()
    watchlists.update_all()

    trade = Trade(orders=orders, portfolio=portfolio, watchlists=watchlists)

    flow = Flow(data)

    while datetime.now() < datetime.combine(datetime.today(), SETTINGS.TIME.END) + timedelta(minutes=15):
        try:
            action = flow.get_action(portfolio, orders)

            if action == FlowAction.DO_NOTHING:
                trade.stop_loss(flow.direction_in_stock)

            elif action == FlowAction.TRADE:
                [trade.sell(direction) for direction in flow.directions_sell]
                trade.buy(flow.direction_buy)
                trade.take_profit(flow.direction_buy)
                flow.direction_in_stock = flow.direction_buy

            elif action == FlowAction.EXIT_TRADING:
                break

            flow.wait_for_data()

        except (ConnectionError, RemoteDisconnected):
            get_client.cache_clear()

    Transactions().log_deals(only_today=True)
