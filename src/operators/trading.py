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
from data.settings import BUDGET, OMX30_AVA, OMX30_YAHOO, TRADING_RESOLUTION
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
        self.latest_candle_timedelta_min = 0
        self.past_orders = []

    def get(self):
        storage = Storage(OMX30_YAHOO, resolution=TRADING_RESOLUTION)

        data = storage.read()
        data_size_before = data.shape[0]

        data_ava = Chart.get_chart_data(OMX30_AVA, TimePeriod.TODAY, Resolution.TWO_MINUTES)
        storage.write(data_ava)

        if data_ava.empty:
            data_yahoo = Ticker(OMX30_YAHOO).get_history(period=Period.ONE_DAY, interval=Interval.TWO_MINUTES)
            storage.write(data_yahoo)

        data = storage.read()
        data_size_after = data.shape[0]

        self.data = data.loc[
            data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=3)
        ]
        self.is_new = data_size_before != data_size_after
        self.latest_candle_timedelta_min = (datetime.now() - self.data.index[-1]).seconds // 60

    def add_signals(self):
        indicators_mapping = get_indicators(self.data)
        self.strategy = get_strategy(indicators_mapping, "strategies.json")

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

        self.data.loc[self.data.between_time("17:14", "17:16").index, "EXIT"] = True

    def get_latest_signal(self) -> Optional[Signal]:
        signal = None

        for i in range(2, 5):
            if self.data.iloc[-i]["EXIT"]:
                signal = Signal.EXIT

            if self.data.iloc[-i]["LONG"] and not self.data.iloc[-i]["SHORT"]:
                signal = Signal.LONG

            elif self.data.iloc[-i]["SHORT"] and not self.data.iloc[-i]["LONG"]:
                signal = Signal.SHORT

            if signal:
                (log.info if i == 2 else log.debug)(
                    f"Trading signal: {signal}. Latest price: {self.data.iloc[-1]['Close']}",
                )
                break

        return signal


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


def _sell_instrument(signal: Signal, orders: Orders, portfolio: Portfolio) -> None:
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


def _buy_instrument(signal: Signal, orders: Orders, watchlist: Watchlists, portfolio: Portfolio) -> None:
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
            volume=BUDGET // instrument_preferred.sell,
        )


def _exit_positions(orders: Orders, portfolio: Portfolio) -> None:
    for position in portfolio.positions:
        orders.place(
            order_book_id=position.instrument.id,
            instrument_name=position.instrument.name,
            order_type=OrderType.SELL,
            price=position.quote.buy,
            volume=int(position.volume),
        )


# MAIN
def trade(dry_run: bool) -> None:
    log.info(f"Started trading strategies on OMX30 | {TRADING_RESOLUTION}" + (" | DRY_RUN" if dry_run else ""))

    data = Data()
    data.get()

    orders = Orders()
    orders.delete_all()

    portfolio = Portfolio()
    portfolio.reload_positions()
    portfolio.reload_balance()

    telegram = Telegram()
    telegram.log_starting_balance(orders, portfolio)

    watchlist = Watchlists()
    watchlist.update_watchlists()

    while datetime.now().time() < datetime.strptime("17:30", "%H:%M").time():
        orders.reload_active()

        if all(
            [
                not orders.active_order,
                not portfolio.positions,
                data.data.iloc[-1].name.time() >= time(17, 0),  # type: ignore
            ],
        ):
            # STOP
            break
        elif any(
            [
                orders.active_order,
                data.is_new,
            ],
        ):
            # TRADE
            data.is_new = False
        elif datetime.now().minute % 2 == 1:
            sleep(62 - datetime.now().second)
            data.get()
            data.is_new = True
            continue
        else:
            sleep(62 - datetime.now().second)
            continue

        if data.latest_candle_timedelta_min > 15:
            log.warning(f"No new data for {data.latest_candle_timedelta_min} mins. Stop trading")
            signal = Signal.EXIT
        else:
            data.add_signals()
            signal = data.get_latest_signal()

        if not signal:
            continue

        portfolio.reload_positions()

        orders.delete_all()

        if signal == Signal.EXIT:
            _exit_positions(orders, portfolio)
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

        _sell_instrument(signal, orders, portfolio)
        _buy_instrument(signal, orders, watchlist, portfolio)

        portfolio.reload_positions()

    portfolio.reload_balance()

    telegram.log_final_balance(portfolio)
    telegram.send_message()

    log.info(f"Finished trading with {data.strategy.name}")
