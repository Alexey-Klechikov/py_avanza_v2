import platform
import warnings
from datetime import datetime, time, timedelta
from enum import Enum
from time import sleep
from typing import Optional

import pandas as pd
from avanza.constants import OrderType, Resolution, TimePeriod

from apis.avanza.operators import Chart, Orders, Portfolio, Watchlists
from apis.telegram.operators import Telegram as TelegramBase
from apis.yahoo.client.models import Interval, Period
from apis.yahoo.operators import Ticker
from data.settings import SETTINGS
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

        data_ava = Chart.get_chart_data(self.settings, TimePeriod.TODAY, Resolution.TWO_MINUTES)
        storage.write(data_ava)

        if data_ava.empty:
            data_yahoo = Ticker(self.settings).get_history(period=Period.ONE_DAY, interval=Interval.TWO_MINUTES)
            storage.write(data_yahoo)

        data = storage.read()
        data_size_after = data.shape[0]

        self.data = data.loc[
            data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=4)
        ]

        self.too_old = ((datetime.now() - self.data.index[-1]).seconds // 60) > 15

        self.is_new = data_size_before != data_size_after

    def get_strategies(self):
        indicators_mapping = get_indicators(self.data)
        strategies = read_top_strategies(indicators_mapping, f"{self.settings.DIR}/strategies.json")
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

            log.info(f"Signal: {signal}. Strategy {i+1}. Latest price: {self.data.iloc[-1]['Close']}")
            return signal


class Budget:
    def __init__(self, settings):
        self.value = settings.MINIMUM_BUDGET
        self.settings = settings
        self.starting_balance = 0

    def adjust(self, orders: Orders, portfolio: Portfolio) -> None:
        self.starting_balance = portfolio.buying_power

        past_orders = orders.get_past()
        for past_order in past_orders:
            if (
                past_order.time.time() <= self.settings.TRADING_START
                or past_order.time.time() >= self.settings.TRADING_END
            ):
                continue

            self.starting_balance += past_order.amount * (1 if past_order.side == "BUY" else -1)

        self.value = int(max([(self.starting_balance // 500 - 4) * 500, self.settings.MINIMUM_BUDGET]))
        if self.value != self.settings.MINIMUM_BUDGET:
            log.warning(f"Budget adjusted: {self.settings.MINIMUM_BUDGET} -> {self.value}")


class Telegram(TelegramBase):
    def __init__(self):
        super().__init__()

        self.starting_balance = 0
        self.final_balance = 0
        self.total_value = 0
        self.deals = []

    def log_starting_balance(self, budget: Budget, portfolio: Portfolio) -> None:
        if portfolio.total_value != portfolio.buying_power:
            self.messages.append("> Order is pending at start")

        self.starting_balance = budget.starting_balance

    def log_final_balance(self, portfolio: Portfolio) -> None:
        if portfolio.total_value != portfolio.buying_power:
            self.messages.append("> Order is pending in the end")

        self.final_balance = portfolio.total_value

    def log_deals(self, orders: Orders, settings) -> None:
        deals = orders.get_past()

        if not deals:
            return

        deals_df = pd.DataFrame([deal.__dict__ for deal in deals])
        for _, group in deals_df.groupby("orderbook_id")[["volume", "price", "amount", "time", "side"]]:
            if len(group) == 1:
                continue
            group.sort_values("time", inplace=True)
            group["amount"] = group.apply(lambda x: x["amount"] * (-1 if x["side"] == "BUY" else 1), axis=1)

            if group["time"].iloc[0].time() <= settings.TRADING_START:
                continue

            self.deals.append((round(group["amount"].sum()), group["time"].iloc[0].strftime("%Y-%m-%d %H:%M:%S")))

        self.deals.sort(key=lambda x: x[1])

    def send_message(self, budget: Budget) -> None:
        self.messages = [
            f"Finished trading with budget: {budget.value}",
            f"Performance: {round(self.final_balance - self.starting_balance)} SEK "
            f"[{round(100 * (self.final_balance - self.starting_balance)/budget.value)} %]",
            f"Total value: {round(self.final_balance)}",
            f"Deals: {len(self.deals)} st. " + (f"{[i[0] for i in self.deals]}" if self.deals else ""),
        ] + self.messages

        super().send_message()


class Trade:
    @classmethod
    def sell(cls, signal: Signal, orders: Orders, portfolio: Portfolio) -> None:
        for tested_signal, instrument_direction_to_sell in [(Signal.LONG, "BEAR"), (Signal.SHORT, "BULL")]:
            if signal != tested_signal:
                continue

            instrument_to_sell = getattr(portfolio.acquired_instrument, instrument_direction_to_sell)
            if not instrument_to_sell:
                continue

            orders.place(
                order_book_id=instrument_to_sell.instrument.id,
                instrument_name=instrument_to_sell.instrument.name,
                order_type=OrderType.SELL,
                price=instrument_to_sell.quote.buy,
                volume=int(instrument_to_sell.volume),
            )

    @classmethod
    def buy(
        cls,
        signal: Optional[Signal],
        orders: Orders,
        watchlist: Watchlists,
        portfolio: Portfolio,
        budget: Budget,
    ) -> None:
        for tested_signal, instrument_direction_to_buy in [(Signal.LONG, "BULL"), (Signal.SHORT, "BEAR")]:
            if signal != tested_signal:
                continue

            instrument_acquired = getattr(portfolio.acquired_instrument, instrument_direction_to_buy)
            if instrument_acquired:
                continue

            watchlist.refresh_watchlists()
            instrument_preferred = getattr(watchlist.preferred_instrument, instrument_direction_to_buy)

            orders.place(
                order_book_id=instrument_preferred.id,
                instrument_name=instrument_preferred.name,
                order_type=OrderType.BUY,
                price=instrument_preferred.sell,
                volume=budget.value // instrument_preferred.sell,
            )

    @classmethod
    def exit(cls, orders: Orders, portfolio: Portfolio) -> None:
        for position in portfolio.positions:
            orders.place(
                order_book_id=position.instrument.id,
                instrument_name=position.instrument.name,
                order_type=OrderType.SELL,
                price=position.quote.buy,
                volume=int(position.volume),
            )


class FlowAction(Enum):
    TRADE = "TRADE"
    DO_NOTHING = "DO_NOTHING"
    EXIT_TRADING = "EXIT_TRADING"
    EXIT_POSITION = "EXIT_POSITION"


class Flow:
    def __init__(self, settings):
        self.action: FlowAction = FlowAction.TRADE
        self.settings = settings

    def decide(self, data: Data, orders: Orders, portfolio: Portfolio) -> None:
        orders.reload_active()
        portfolio.reload_positions()

        if all(
            [
                not orders.active_order,
                not portfolio.positions,
                datetime.now().time() >= self.settings.TRADING_END,
            ],
        ):
            self.action = FlowAction.EXIT_TRADING
        elif any(
            [
                data.too_old,
                datetime.now().time() >= self.settings.TRADING_END,
            ],
        ):
            self.action = FlowAction.EXIT_POSITION
        elif any(
            [
                orders.active_order,
                data.is_new,
            ],
        ):
            data.get_strategies()
            data.is_new = False
            self.action = FlowAction.TRADE
        else:
            sleep(120 - ((datetime.now().minute * 60 + datetime.now().second) % 120) + 2)
            data.get()
            self.action = FlowAction.DO_NOTHING

        if orders.active_order:
            orders.delete_all()


# MAIN
def trade(dry_run: bool, settings) -> None:
    log.info(
        f"Start trading strategies on {settings.NAME} | {settings.RESOLUTION}" + (" | DRY_RUN" if dry_run else ""),
    )

    data = Data(settings)
    data.get()

    orders = Orders()
    orders.delete_all()

    portfolio = Portfolio()
    portfolio.reload_positions()
    portfolio.reload_balance()

    budget = Budget(settings)
    budget.adjust(orders, portfolio)

    telegram = Telegram()
    telegram.log_starting_balance(budget, portfolio)

    watchlist = Watchlists(settings)
    watchlist.update_watchlists()

    flow = Flow(settings)

    while datetime.now().time() < time(22, 10):
        flow.decide(data, orders, portfolio)
        if flow.action == FlowAction.DO_NOTHING:
            continue
        elif flow.action == FlowAction.EXIT_TRADING:
            break
        elif flow.action == FlowAction.EXIT_POSITION:
            signal = Signal.EXIT
        elif flow.action == FlowAction.TRADE:
            signal = data.get_signal()

        if not signal:
            continue

        if signal == Signal.EXIT:
            Trade.exit(orders, portfolio)
            continue

        portfolio.detect_acquired_instruments()
        if any(
            [
                signal == Signal.LONG and portfolio.acquired_instrument.BULL,
                signal == Signal.SHORT and portfolio.acquired_instrument.BEAR,
                dry_run,
            ],
        ):
            continue

        Trade.sell(signal, orders, portfolio)

        orders.reload_active()
        if orders.active_order:
            continue

        Trade.buy(signal, orders, watchlist, portfolio, budget)

    portfolio.reload_balance()

    telegram.log_final_balance(portfolio)
    telegram.log_deals(orders, settings)
    telegram.send_message(budget)


if __name__ == "__main__":
    try:
        trade(dry_run=(True if platform.system() == "Darwin" else False), settings=SETTINGS.OMX)
        trade(dry_run=(True if platform.system() == "Darwin" else False), settings=SETTINGS.NASDAQ)

    except Exception as e:
        telegram = TelegramBase()
        telegram.messages = ["Error in task_trade.py"]
        telegram.send_message()

        raise e
