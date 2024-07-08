import warnings
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel

from data.settings import OMX30_YAHOO
from services.storage import Storage
from services.ta.figure import Figure
from services.ta.indicators.models import Indicator, Panel, Plot, Plots
from services.ta.operators import get_indicators
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)


set_handlers("development")
log = get_logger()

LOG_INDIVIDUAL_TRADES = False

data = pd.DataFrame()


class Order(BaseModel):
    buy_price: float
    buy_datetime: Any
    sell_price: Optional[float] = None
    sell_datetime: Optional[Any] = None

    def sell(self, sell_price: float, sell_datetime: Any, instrument_type: str) -> float:
        self.sell_price = sell_price
        self.sell_datetime = sell_datetime

        profit = self.sell_price - self.buy_price - 0.1
        profit = profit if instrument_type == "BULL" else -profit

        trading_time = (self.sell_datetime - self.buy_datetime).seconds / 60

        if LOG_INDIVIDUAL_TRADES:
            log.info(
                f"{self.buy_datetime.date()} {instrument_type}: "
                f"{round(self.buy_price, 2)} -> {round(self.sell_price, 2)} "
                f"at {self.buy_datetime.time()} -> {self.sell_datetime.time()}: "
                f"{round(profit, 2)} in {trading_time} min"
                f" ({('+' if profit > 0 else '-') * (1 + int(round(abs(profit)) // 3))})",
            )

        return profit


class Wallet(BaseModel):
    BULL: Optional[Order] = None
    BEAR: Optional[Order] = None


class Counter(BaseModel):
    total_trades: int = 0
    total_profit: float = 0


class Strategy:
    def __init__(
        self,
        all_indicators: Dict[str, Dict[str, Indicator]],
        selected_indicators: Tuple[Tuple[str, str], Tuple[str, str], Tuple[str, str]],
        counter: Counter = Counter(),
    ):
        self.counter = counter
        self.selected_indicators = selected_indicators

        self.indicators_logic: List[Indicator] = []
        for category, name in selected_indicators:
            indicator = all_indicators.get(category, {}).get(name)
            if not indicator:
                log.warning(f"Indicator {name} from category {category} does not exist.")
                continue

            if indicator.plots is None:
                log.warning(f"Indicator {name}-{category} does not have any plots.")
                continue

            self.indicators_logic.append(indicator)


def _consider_signals(strategy: Strategy):
    for column in ["LONG", "SHORT", "EXIT", "STOP_LOSS_LONG", "STOP_LOSS_SHORT"]:
        combination_condition = all if column in ["LONG", "SHORT"] else any

        signal_methods = [
            indicator.signal.__getattribute__(column)
            for indicator in strategy.indicators_logic
            if indicator.signal.__getattribute__(column) is not None
        ]

        for i, row in data.iterrows():
            data.at[i, column] = (
                np.nan
                if not signal_methods or not combination_condition(signal_method(row) for signal_method in signal_methods)
                else row[column]
            )

    for column in ["LONG", "SHORT", "EXIT"]:
        for non_trading_time in (["09:00", "10:00"], ["17:15", "17:30"]):
            data.loc[data.between_time(non_trading_time[0], non_trading_time[1]).index, column] = np.nan

        data.loc[data.between_time("17:15", "17:16").index, "EXIT"] = (data["High"] + data["Low"]) / 2


def _consider_trading_logic(strategy: Strategy):
    wallet = Wallet()

    for i, row in data.iterrows():
        profit = None
        if (
            wallet.BULL is None
            and row["LONG"] > 0
            and np.isnan(row["STOP_LOSS_LONG"])
            and np.isnan(row["EXIT"])
            and np.isnan(row["SHORT"])
        ):
            wallet.BULL = Order(buy_price=row["LONG"], buy_datetime=i)

            if wallet.BEAR is not None:
                profit = wallet.BEAR.sell(row["LONG"], i, "BEAR")
                wallet.BEAR = None

        elif wallet.BULL is not None and (row["STOP_LOSS_LONG"] > 0 or row["EXIT"] > 0):
            sell_price = row["STOP_LOSS_LONG"] if row["STOP_LOSS_LONG"] > 0 else row["EXIT"]
            profit = wallet.BULL.sell(sell_price, i, "BULL")
            data.at[i, "EXIT"] = sell_price
            wallet.BULL = None

        if (
            wallet.BEAR is None
            and row["SHORT"] > 0
            and np.isnan(row["STOP_LOSS_SHORT"])
            and np.isnan(row["EXIT"])
            and np.isnan(row["LONG"])
        ):
            wallet.BEAR = Order(buy_price=row["SHORT"], buy_datetime=i)

            if wallet.BULL is not None:
                profit = wallet.BULL.sell(row["SHORT"], i, "BULL")
                wallet.BULL = None

        elif wallet.BEAR is not None and (row["STOP_LOSS_SHORT"] > 0 or row["EXIT"] > 0):
            sell_price = row["STOP_LOSS_SHORT"] if row["STOP_LOSS_SHORT"] > 0 else row["EXIT"]
            profit = wallet.BEAR.sell(sell_price, i, "BEAR")
            data.at[i, "EXIT"] = sell_price
            wallet.BEAR = None

        if profit is not None:
            strategy.counter.total_trades += 1
            strategy.counter.total_profit += profit


def add_signals(data: pd.DataFrame, strategy: Strategy):
    data["LONG"] = data["High"]
    data["SHORT"] = data["Low"]
    data["EXIT"] = (data["High"] + data["Low"]) / 2
    data["STOP_LOSS_LONG"] = data["Low"]
    data["STOP_LOSS_SHORT"] = data["High"]

    _consider_signals(strategy)
    _consider_trading_logic(strategy)


def plot_indicators(strategy: Strategy):
    figure = Figure(data=data)
    for indicator in strategy.indicators_logic:
        figure.add_plot(indicator.plots)

    plot_signals = Plots(
        panel=Panel.MAIN,
        list=[
            Plot(columns=[column], type="scatter", color=color, markersize=50)
            for column, color in [("LONG", "green"), ("SHORT", "red"), ("EXIT", "black")]
            if not data[column].isnull().all()
        ],
    )

    figure.add_plot(plot_signals)

    figure.show()


if __name__ == "__main__":
    data = Storage(OMX30_YAHOO, resolution="5m").read()
    data = data.loc[data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=50)]

    indicators = get_indicators(data)
    indicators_selector: List[Tuple[str, str]] = [
        ("Trend", "CKSP"),  # stop loss   --- 98 m  --- 26.12
        ("Trend", "ADX"),  # buy / sell   --- 1 fixed
        ("Trend", "TII"),  # buy / sell   --- 1 fixed
        ("Trend", "PSAR"),  # buy / sell  --- 8 m --- 79.76
        ("Trend", "CHOP"),  # exit      --- 44 m ---- 44.7
        ("Overlap", "LINREG"),  # buy / sell  --- 11 m --- 77.71
        ("Overlap", "GHLA"),  # buy / sell --- 6 fixed
        ("Momentum", "MACD_DEMA"),  # buy / sell --- 14 fixed -- 73.13
        ("Momentum", "STC"),  # buy / sell --- 1 fixed
        ("Momentum", "CCI"),  # buy / sell --- 12 m - 77.16
        ("Momentum", "RVGI"),  # buy / sell  --- 2 fixed
        ("Momentum", "STOCH"),  # buy / sell  --- 3 fixed
        ("Cycles", "EBSW"),  # buy / sell -> only use for confirmation --- 5 fixed
        ("Volatility", "STARC"),  # buy / sell  --- 26 m --- 61.63
        ("Volatility", "MASSI"),  # buy / sell -> only use as a filter  --- 23 m --- 62.98
        ("Volatility", "BBANDS"),  # buy / sell  --- 2 fixed
        ("Volatility", "ACCBANDS"),  # buy / sell | stop loss  --- 70 m ---- 33.16
        # ("Volume", "PVT"),  # buy / sell
        # ("Volume", "ADOSC"),  # buy / sell
        # ("Volume", "CMF"),  # buy / sell (exit?)
        # ("Volume", "KVO"),  # buy / sell
    ]

    strategies: List[Strategy] = []
    for i1, indicator1 in enumerate(indicators_selector):
        for i2, indicator2 in enumerate(indicators_selector[i1 + 1 :]):
            for i3, indicator3 in enumerate(indicators_selector[i1 + i2 + 2 :]):
                strategies.append(
                    deepcopy(
                        Strategy(
                            selected_indicators=(indicator1, indicator2, indicator3),
                            all_indicators=indicators,
                        ),
                    ),
                )

    for i, strategy in enumerate(strategies):
        if i != 0 and i % 10 == 0:
            log.info(f"Strategy {i}/{len(strategies)}")

        add_signals(data=data, strategy=strategy)
        # plot_indicators(strategy=strategy)

    for strategy in sorted(strategies, key=lambda x: x.counter.total_profit, reverse=True):
        log.info(
            "Indicators: "
            f'{" | ".join([(category + "-" + indicator) for category, indicator in strategy.selected_indicators])}. '
            f"Total trades: {strategy.counter.total_trades} | Total profit: {round(strategy.counter.total_profit, 2)}",
        )
