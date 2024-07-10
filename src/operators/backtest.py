import os
import warnings
from typing import Any, List, Optional, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel

from data.settings import BACKTEST_LOG_INDIVIDUAL_TRADES
from services.ta import Figure, get_indicators, get_strategies, save_strategies
from services.ta.indicators.models import Panel, Plot, Plots
from services.ta.strategies.models import ComposeStrategiesListMethod, Strategy
from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)


log = get_logger()


class Order(BaseModel):
    buy_price: float
    buy_datetime: Any
    sell_price: Optional[float] = None
    sell_datetime: Optional[Any] = None

    def sell(self, sell_price: float, sell_datetime: Any, instrument_type: str) -> float:
        self.sell_price = sell_price
        self.sell_datetime = sell_datetime

        profit = self.sell_price - self.buy_price
        profit = profit if instrument_type == "LONG" else -profit
        profit -= 0.4  # Spread

        trading_time = (self.sell_datetime - self.buy_datetime).seconds / 60

        if BACKTEST_LOG_INDIVIDUAL_TRADES:
            log.info(
                f"{self.buy_datetime.date()} {instrument_type}: "
                f"{round(self.buy_price, 2)} -> {round(self.sell_price, 2)} "
                f"at {self.buy_datetime.time()} -> {self.sell_datetime.time()}: "
                f"{round(profit, 2)} in {trading_time} min"
                f" ({('+' if profit > 0 else '-') * (1 + int(round(abs(profit)) // 3))})",
            )

        return profit


class Wallet(BaseModel):
    LONG: Optional[Order] = None
    SHORT: Optional[Order] = None


def _consider_signals(data: pd.DataFrame, strategy: Strategy):
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


def _consider_trading_logic(data: pd.DataFrame, strategy: Strategy):
    wallet = Wallet()

    for i, row in data.iterrows():
        profit = None
        if (
            wallet.LONG is None
            and row["LONG"] > 0
            and np.isnan(row["STOP_LOSS_LONG"])
            and np.isnan(row["EXIT"])
            and np.isnan(row["SHORT"])
        ):
            wallet.LONG = Order(buy_price=row["LONG"], buy_datetime=i)

            if wallet.SHORT is not None:
                profit = wallet.SHORT.sell(row["LONG"], i, "SHORT")
                wallet.SHORT = None

        elif wallet.LONG is not None and (row["STOP_LOSS_LONG"] > 0 or row["EXIT"] > 0):
            sell_price = row["STOP_LOSS_LONG"] if row["STOP_LOSS_LONG"] > 0 else row["EXIT"]
            profit = wallet.LONG.sell(sell_price, i, "LONG")
            data.at[i, "EXIT"] = sell_price
            wallet.LONG = None

        if (
            wallet.SHORT is None
            and row["SHORT"] > 0
            and np.isnan(row["STOP_LOSS_SHORT"])
            and np.isnan(row["EXIT"])
            and np.isnan(row["LONG"])
        ):
            wallet.SHORT = Order(buy_price=row["SHORT"], buy_datetime=i)

            if wallet.LONG is not None:
                profit = wallet.LONG.sell(row["SHORT"], i, "LONG")
                wallet.LONG = None

        elif wallet.SHORT is not None and (row["STOP_LOSS_SHORT"] > 0 or row["EXIT"] > 0):
            sell_price = row["STOP_LOSS_SHORT"] if row["STOP_LOSS_SHORT"] > 0 else row["EXIT"]
            profit = wallet.SHORT.sell(sell_price, i, "SHORT")
            data.at[i, "EXIT"] = sell_price
            wallet.SHORT = None

        if profit is not None:
            strategy.counter.total_trades += 1
            strategy.counter.total_profit += profit
            strategy.counter.profitable_trades += 1 if profit > 0 else 0


def add_signals(data: pd.DataFrame, strategy: Strategy):
    data["LONG"] = data["High"]
    data["SHORT"] = data["Low"]
    data["EXIT"] = (data["High"] + data["Low"]) / 2
    data["STOP_LOSS_LONG"] = data["Low"]
    data["STOP_LOSS_SHORT"] = data["High"]

    _consider_signals(data, strategy)
    _consider_trading_logic(data, strategy)


def print_strategies_performance(strategies: List[Strategy]) -> None:
    for strategy in strategies:
        if strategy.counter.total_profit <= 0:
            break

        log.info(
            f"{strategy.name}. Trades: {strategy.counter.total_trades}. "
            f"Profit: {round(strategy.counter.total_profit, 2)}. "
            f"Profitable trades: {round(100 * strategy.counter.profitable_trades / strategy.counter.total_trades)}%",
        )


def plot_indicators(data: pd.DataFrame, strategy: Strategy):
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


def get_file_path(filename: Optional[str]) -> Optional[str]:
    if not filename:
        return

    current_file_path = os.path.abspath(__file__)
    root_dir = "/src" if "/src" in current_file_path else "/pyAvanza"
    return current_file_path.split(root_dir)[0] + f"{root_dir}/data/{filename}"


# MAIN
def backtest(
    data: pd.DataFrame,
    indicators_selector: List[Tuple[str, str]],
    compose_strategies_list_method: ComposeStrategiesListMethod,
    indicators_filter: Optional[List[str]] = None,
    old_strategies_filename: Optional[str] = None,
    new_strategies_filename: Optional[str] = None,
    plot: bool = False,
) -> None:
    indicators = get_indicators(data)

    strategies = get_strategies(
        compose_strategies_list_method,
        indicators,
        indicators_selector,
        old_strategies_file_path=get_file_path(old_strategies_filename),
    )

    if indicators_filter:
        strategies = [
            strategy for strategy in strategies if all(indicator in strategy.name for indicator in indicators_filter)
        ]

    for i, strategy in enumerate(strategies):
        if BACKTEST_LOG_INDIVIDUAL_TRADES:
            log.info(f"Strategy {i + 1}/{len(strategies)}: {strategy.name}")

        add_signals(data, strategy)

        if plot:
            plot_indicators(data, strategy)

    strategies.sort(key=lambda x: x.counter.total_profit, reverse=True)
    print_strategies_performance(strategies)

    if new_strategies_filename:
        save_strategies(strategies, new_strategies_file_path=get_file_path(new_strategies_filename))
