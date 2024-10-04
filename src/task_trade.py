import platform
import warnings
from datetime import datetime, time, timedelta
from enum import Enum
from time import sleep
from typing import List, Optional

import pandas as pd
from avanza.constants import OrderType, Resolution, TimePeriod

from apis.avanza.operators import Chart, Orders, Portfolio, Watchlists
from apis.telegram.operators import Telegram as TelegramBase
from apis.yahoo.client.models import Interval, Period
from apis.yahoo.operators import Ticker
from config import SETTINGS_TRADE_OMX
from services.storage import Storage
from services.ta import get_indicators, read_top_strategies
from services.ta.strategies.models import Strategy
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

set_handlers("trade")
log = get_logger()


class Signal(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    EXIT = "EXIT"


class Direction(Enum):
    BULL = "BULL"
    BEAR = "BEAR"


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

        if self.settings.TRADING_DATA == "yahoo":
            new_data = Ticker(self.settings).get_history(period=Period.ONE_DAY, interval=Interval.TWO_MINUTES)

        storage.write(new_data)

        data = storage.read()
        data_size_after = data.shape[0]

        self.data = data.loc[
            data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=4)
        ]

        self.too_old = ((datetime.now() - self.data.index[-1]).seconds // 60) > 15
        self.is_new = data_size_before != data_size_after

    def get_strategies(self):
        indicators_mapping = get_indicators(self.data, self.settings)
        strategies = read_top_strategies(indicators_mapping, f"{self.settings.FILE_PREFIX}_strategies.json")
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

    def get_signal(self) -> Optional[Signal]:
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


class Budget:
    def __init__(self, settings):
        self.value = settings.BUDGET_MINIMUM
        self.settings = settings

    def adjust(self, orders: Orders, portfolio: Portfolio) -> None:
        if datetime.now().time() < time(10, 0):
            starting_balance = portfolio.total_value

        else:
            starting_balance = portfolio.buying_power

            deals = orders.get_past()
            if deals:
                deals_df = pd.DataFrame([deal.__dict__ for deal in deals])
                deals_df.sort_values("time", inplace=True)
                deals_df = deals_df[deals_df["time"].dt.time >= self.settings.TRADING_START]
                deals_df["amount"] = deals_df.apply(lambda x: x["amount"] * (-1 if x["side"] == "BUY" else 1), axis=1)

                starting_balance -= deals_df["amount"].sum()

            if portfolio.positions:
                starting_balance += sum([position.value for position in portfolio.positions])

        self.value = int(max([starting_balance * self.settings.BUDGET_PERCENT, self.settings.BUDGET_MINIMUM]))
        if self.value > self.settings.BUDGET_MINIMUM:
            log.info(f"Budget adjusted: {self.settings.BUDGET_MINIMUM} -> {self.value}")


class Telegram(TelegramBase):
    def __init__(self):
        super().__init__()

        self.final_balance = 0
        self.total_value = 0
        self.deals = []

    def log_final_balance(self, portfolio: Portfolio) -> None:
        self.final_balance = portfolio.total_value

    def log_deals(self, orders: Orders) -> None:
        deals = orders.get_past()
        if not deals:
            return

        deals_df = pd.DataFrame([deal.__dict__ for deal in deals])
        for _, group in deals_df.groupby("orderbook_id")[["amount", "time", "side"]]:
            if len(group) == 1:
                continue

            group.sort_values("time", inplace=True)
            group["amount"] = group.apply(lambda x: x["amount"] * (-1 if x["side"] == "BUY" else 1), axis=1)

            group_sum = 0
            deal_time = None
            for i, (_, row) in enumerate(group.iterrows()):
                if i == 0 and row["side"] == "SELL":
                    continue

                if not deal_time:
                    deal_time = row["time"].strftime("%Y-%m-%d %H:%M:%S")

                group_sum += row["amount"]

            self.deals.append((round(group_sum), deal_time))

        self.deals.sort(key=lambda x: x[1])

    def send_message(self, budget: Budget, settings) -> None:
        performance = 0
        if self.deals:
            performance = round(sum([i[0] for i in self.deals]))

        self.messages = [
            f"Finished trading {settings.NAME} with budget: {budget.value}",
            f"Performance: {performance} SEK [{round(100 * (performance)/budget.value)} %]",
            f"Total value: {round(self.final_balance)}",
            f"Deals: {len(self.deals)} st. " + (f"{[i[0] for i in self.deals]}" if self.deals else ""),
        ] + self.messages

        super().send_message()


class Trade:
    @classmethod
    def sell(
        cls,
        direction: Direction,
        orders: Orders,
        portfolio: Portfolio,
    ) -> None:
        for _ in range(5):
            orders.delete_all()

            portfolio.reload_positions(caller="sell")
            acquired_instrument = portfolio.acquired_instrument.get(direction.value)
            if not acquired_instrument:
                return

            orders.place(
                order_book_id=acquired_instrument.instrument.id,
                instrument_name=acquired_instrument.instrument.name,
                order_type=OrderType.SELL,
                price=acquired_instrument.quote.buy,
                volume=int(acquired_instrument.volume),
            )

    @classmethod
    def buy(
        cls,
        direction: Direction,
        orders: Orders,
        watchlists: Watchlists,
        portfolio: Portfolio,
        budget: Budget,
    ) -> None:
        for _ in range(5):
            orders.delete_all()

            portfolio.reload_positions(caller="buy")
            acquired_instrument = portfolio.acquired_instrument.get(direction.value)
            if acquired_instrument:
                return

            watchlists.refresh_all(filter_orderbook_type="WARRANT")
            instrument_preferred = watchlists.preferred_instrument.get(direction.value)
            if not instrument_preferred or not instrument_preferred.sell:
                continue

            orders.place(
                order_book_id=instrument_preferred.id,
                instrument_name=instrument_preferred.name,
                order_type=OrderType.BUY,
                price=instrument_preferred.sell,
                volume=round(budget.value // instrument_preferred.sell),
            )

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
            price=round(acquired_instrument.quote.sell * (1 + take_profit), 2),
            volume=int(acquired_instrument.volume),
        )


class FlowAction(Enum):
    TRADE = "TRADE"
    DO_NOTHING = "DO_NOTHING"
    EXIT_TRADING = "EXIT_TRADING"


class Flow:
    def __init__(self, settings, dry_run=False):
        self.trading_ends: time = settings.TRADING_END
        self.stop_loss: float = settings.TRADING_STOP_LOSS
        self.dry_run: bool = dry_run

        self.directions_sell: List[Direction] = []
        self.directions_buy: List[Direction] = []

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
                    self.directions_sell = [direction]
                    return FlowAction.TRADE

        # Edge case: Sell BEAR at 14:24 if last signal was more than 2.5 hours ago
        if datetime.now().time() == time(14, 26) and portfolio.acquired_instrument.BEAR:
            orders.reload_active()
            if orders.active_order:
                if (datetime.now() - orders.active_order.created).total_seconds() > (2.5 * 60 * 60):
                    self.directions_sell = [Direction.BEAR]
                    return FlowAction.TRADE

        # End of day
        if datetime.now().time() >= self.trading_ends:
            if not portfolio.acquired_instrument.BEAR:
                return FlowAction.EXIT_TRADING

            self.directions_sell = [Direction.BEAR]
            return FlowAction.TRADE

        # Near end of day
        elif (datetime.now() + timedelta(minutes=10)).time() >= self.trading_ends:
            if not portfolio.acquired_instrument.BEAR or self.dry_run:
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
    log.warning(
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

    budget = Budget(settings)
    budget.adjust(orders, portfolio)

    telegram = Telegram()

    watchlists = Watchlists(settings)
    watchlists.update_all()

    flow = Flow(settings, dry_run)

    while datetime.now().time() < time(17, 4):
        action = flow.get_action(data, portfolio, orders)
        if action == FlowAction.DO_NOTHING:
            continue
        elif action == FlowAction.EXIT_TRADING:
            break
        elif action == FlowAction.TRADE:
            pass

        for direction in flow.directions_sell:
            Trade.sell(direction, orders, portfolio)

        for direction in flow.directions_buy:
            Trade.buy(direction, orders, watchlists, portfolio, budget)
            Trade.take_profit(direction, orders, portfolio, settings.TRADING_TAKE_PROFIT)

    portfolio.reload_balance()

    telegram.log_final_balance(portfolio)
    telegram.log_deals(orders)
    telegram.send_message(budget, settings)


if __name__ == "__main__":
    try:
        dry_run = platform.system() == "Darwin"

        trade(dry_run, SETTINGS_TRADE_OMX)

    except Exception as e:
        log.exception(str(e))

        telegram = TelegramBase()
        telegram.messages = ["Error in task_trade.py"]
        telegram.send_message()

        raise e
