import warnings
from datetime import datetime, timedelta
from enum import Enum
from time import sleep
from typing import Optional

import pandas as pd
from avanza.constants import OrderType, Resolution, TimePeriod

from apis.avanza.operators import Chart, Orders, Portfolio, Watchlists
from apis.telegram.operators import Telegram as TelegramBase
from apis.yahoo.client.models import Interval, Period
from apis.yahoo.operators import Ticker
from data.settings import BUDGET, OMX30_AVA, OMX30_YAHOO
from services.storage import Storage
from services.ta import get_indicators, get_strategy
from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)


log = get_logger()


class Signal(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    EXIT = "EXIT"


class Data:
    def __init__(self):
        self.data: pd.DataFrame = pd.DataFrame()
        self.is_new = False
        self.past_orders = []

    def get(self):
        storage = Storage(OMX30_YAHOO, resolution=Interval.FIVE_MINUTES.value.raw)

        data = storage.read()
        data_size_before = data.shape[0]

        data_ava = Chart.get_chart_data(OMX30_AVA, TimePeriod.TODAY, Resolution.FIVE_MINUTES)
        storage.write(data_ava)

        if data_ava.empty:
            data_yahoo = Ticker(OMX30_YAHOO).get_history(period=Period.ONE_DAY, interval=Interval.FIVE_MINUTES)
            storage.write(data_yahoo)

        data = storage.read()
        data_size_after = data.shape[0]

        self.data = data.loc[
            data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=4)
        ]
        self.is_new = data_size_before != data_size_after

    def add_signals(self):
        indicators = get_indicators(self.data)
        self.strategy = get_strategy(indicators, "strategies.json")

        self.data["LONG"] = False
        self.data["SHORT"] = False
        self.data["EXIT"] = False

        for column in ["LONG", "SHORT", "EXIT"]:
            combination_condition = all if column in ["LONG", "SHORT"] else any

            signal_methods = [
                indicator.signal.__getattribute__(column)
                for indicator in self.strategy.indicators_logic
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
            for non_trading_time in (["09:00", "10:00"], ["17:15", "17:30"]):
                self.data.loc[self.data.between_time(non_trading_time[0], non_trading_time[1]).index, column] = False

        self.data.loc[self.data.between_time("17:15", "17:30").index, "EXIT"] = True

    def get_latest_signal(self) -> Optional[Signal]:
        for i in range(1, 5):
            if self.data.iloc[-i]["LONG"] and not self.data.iloc[-i]["SHORT"] and not self.data.iloc[-i]["EXIT"]:
                return Signal.LONG

            elif self.data.iloc[-i]["SHORT"] and not self.data.iloc[-i]["LONG"] and not self.data.iloc[-i]["EXIT"]:
                return Signal.SHORT

            elif self.data.iloc[-i]["EXIT"]:
                return Signal.EXIT


class Telegram(TelegramBase):
    def __init__(self):
        super().__init__()

        self.starting_balance = 0
        self.final_balance = 0
        self.total_value = 0

    def log_starting_balance(self, orders: Orders, portfolio: Portfolio) -> None:
        if portfolio.total_value != portfolio.buying_power:
            self.messages.append("> Order is pending at start")

        self.starting_balance = portfolio.buying_power

        past_orders = orders.get_past()
        for i, past_order in enumerate(past_orders):
            if i == 0 and past_order.side == "SELL":
                self.messages.append("> Carry on position from yesterday")

            self.starting_balance += past_order.amount * (1 if past_order.side == "BUY" else -1)

    def log_final_balance(self, portfolio: Portfolio) -> None:
        if portfolio.total_value != portfolio.buying_power:
            self.messages.append("> Order is pending in the end")

        self.final_balance = portfolio.buying_power
        self.total_value = portfolio.total_value

    def send_message(self):
        self.messages = [
            f"Finished trading with budget: {BUDGET}",
            f"Performance: {round(self.final_balance - self.starting_balance)} SEK "
            f"[{round(100 * (self.final_balance - self.starting_balance)/BUDGET)} %]",
            f"Total value: {round(self.total_value)}",
        ] + self.messages

        super().send_message()


# MAIN
def trade():
    log.info("Started trading strategies on OMX30 | 5m")

    data = Data()

    orders = Orders()
    orders.delete_all()

    portfolio = Portfolio()
    portfolio.reload_balance()

    telegram = Telegram()
    telegram.log_starting_balance(orders, portfolio)

    watchlist = Watchlists()
    watchlist.update_watchlists()
    watchlist.refresh_watchlists()

    while datetime.now().time() < datetime.strptime("17:30", "%H:%M").time():
        data.get()
        orders.reload_active()

        if not data.is_new and not orders.active_order:
            sleep(30)
            continue

        data.add_signals()
        signal = data.get_latest_signal()
        if not signal:
            continue

        log.info(f"Trading signal: {signal}")

        portfolio.reload_positions()
        orders.delete_all()

        if signal == Signal.EXIT:
            for position in portfolio.positions:
                orders.place(
                    order_book_id=position.instrument.id,
                    order_type=OrderType.SELL,
                    price=position.quote.buy,
                    volume=int(position.volume),
                )
            continue

        portfolio.detect_acquired_instruments(
            instrument_type_to_id_mapping={
                instrument_direction: [i["id"] for i in instruments]
                for instrument_direction, instruments in watchlist.valid_instruments.model_dump().items()
            },
        )

        for tested_signal, instrument_direction_to_sell in [(Signal.LONG, "BEAR"), (Signal.SHORT, "BULL")]:
            if signal != tested_signal:
                continue

            instrument_to_sell = getattr(portfolio.acquired_instrument, instrument_direction_to_sell)
            if not instrument_to_sell:
                continue

            orders.place(
                order_book_id=instrument_to_sell.instrument.id,
                order_type=OrderType.SELL,
                price=instrument_to_sell.quote.buy,
                volume=int(instrument_to_sell.volume),
            )
            sleep(5)

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
                order_type=OrderType.BUY,
                price=instrument_preferred.sell,
                volume=BUDGET // instrument_preferred.sell,
            )

    portfolio.reload_balance()

    telegram.log_final_balance(portfolio)
    telegram.send_message()

    log.info(f"Finished trading with {data.strategy.name}")
