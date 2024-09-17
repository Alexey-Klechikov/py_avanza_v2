import warnings
from typing import Any, List, Optional

import numpy as np
import pandas as pd
from pathos.multiprocessing import ProcessingPool as Pool
from pydantic import BaseModel

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
        profit -= self.buy_price * 0.01 * 0.02  # Spread

        if profit > self.buy_price * 0.01:
            profit = self.buy_price * 0.01

        return profit


class Wallet(BaseModel):
    LONG: Optional[Order] = None
    SHORT: Optional[Order] = None


def _consider_signals(data: pd.DataFrame, strategy: Strategy, settings) -> None:
    for column in ["LONG", "SHORT", "EXIT"]:
        combination_condition = all if column in ["LONG", "SHORT"] else any

        signal_methods = [
            indicator.signal.__getattribute__(column)
            for indicator in strategy.indicators_logic
            if indicator.signal.__getattribute__(column) is not None
        ]

        data[column] = data.apply(
            lambda row: (
                np.nan
                if not signal_methods or not combination_condition(signal_method(row) for signal_method in signal_methods)
                else row[column]
            ),
            axis=1,
        )

    for column in ["LONG", "SHORT", "EXIT"]:
        for non_trading_time in (
            ["09:00", settings.TRADING_START.strftime("%H:%M")],
            [settings.TRADING_END.strftime("%H:%M"), "23:00"],
        ):
            data.loc[data.between_time(non_trading_time[0], non_trading_time[1]).index, column] = np.nan

    data.loc[data.between_time(settings.TRADING_END.strftime("%H:%M"), "22:00").index, "EXIT"] = (
        data["High"] + data["Low"]
    ) / 2


def _consider_trading_logic(data: pd.DataFrame, strategy: Strategy):
    wallet = Wallet()

    for i, row in data[data["LONG"].notna() | data["SHORT"].notna() | data["EXIT"].notna()][
        ["LONG", "SHORT", "EXIT"]
    ].iterrows():
        profit = None

        # LONG
        if wallet.LONG is None and row["LONG"] > 0 and np.isnan(row["EXIT"]) and np.isnan(row["SHORT"]):
            wallet.LONG = Order(buy_price=row["LONG"], buy_datetime=i)

            if wallet.SHORT is not None:
                profit = wallet.SHORT.sell(row["LONG"], i, "SHORT")
                wallet.SHORT = None

        if wallet.LONG is not None and row["EXIT"] > 0:
            sell_price = row["EXIT"]
            profit = wallet.LONG.sell(sell_price, i, "LONG")
            wallet.LONG = None

        # SHORT
        if wallet.SHORT is None and row["SHORT"] > 0 and np.isnan(row["EXIT"]) and np.isnan(row["LONG"]):
            wallet.SHORT = Order(buy_price=row["SHORT"], buy_datetime=i)

            if wallet.LONG is not None:
                profit = wallet.LONG.sell(row["SHORT"], i, "LONG")
                wallet.LONG = None

        if wallet.SHORT is not None and row["EXIT"] > 0:
            sell_price = row["EXIT"]
            profit = wallet.SHORT.sell(sell_price, i, "SHORT")
            wallet.SHORT = None

        if profit is not None:
            strategy.counter.total_trades += 1
            strategy.counter.total_profit += profit
            strategy.counter.profitable_trades += 1 if profit > 0 else 0


def process_strategy(kwargs: dict) -> Strategy:
    data: pd.DataFrame = kwargs["data"]
    strategy: Strategy = kwargs["strategy"]
    settings = kwargs["settings"]
    strategy_rank: Optional[str] = kwargs.get("strategy_rank")

    data["LONG"] = data["High"]
    data["SHORT"] = data["Low"]
    data["EXIT"] = (data["High"] + data["Low"]) / 2

    _consider_signals(data, strategy, settings)
    _consider_trading_logic(data, strategy)

    log.debug(
        f"Strategy{strategy_rank if strategy_rank else ''}: {strategy.name} ({round(strategy.counter.total_profit)})",
    )

    return strategy


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


# MAIN
def backtest(
    data: pd.DataFrame,
    compose_strategies_list_method: ComposeStrategiesListMethod,
    settings,
    indicators_filter: Optional[List[str]] = None,
    old_strategies_file_name: Optional[str] = None,
    new_strategies_file_name: Optional[str] = None,
    plot: bool = False,
    **kwargs,
) -> None:
    indicators_mapping = get_indicators(data, settings, **kwargs)

    strategies = get_strategies(
        compose_strategies_list_method,
        indicators_mapping,
        None if not old_strategies_file_name else f"{settings.FILE_PREFIX}_{old_strategies_file_name}",
    )

    if indicators_filter:
        strategies = [
            strategy for strategy in strategies if any(indicator in strategy.name for indicator in indicators_filter)
        ]

    with Pool() as pool:
        strategies = list(
            pool.map(
                process_strategy,
                [
                    {
                        "data": data,
                        "strategy": strategy,
                        "settings": settings,
                        "strategy_rank": f" {i+1} / {len(strategies)}",
                    }
                    for i, strategy in enumerate(strategies)
                ],
            ),
        )

    if plot:
        for strategy in strategies:
            process_strategy({"data": data, "strategy": strategy, "settings": settings})
            plot_indicators(data, strategy)

    strategies = [strategy for strategy in strategies if strategy.counter.total_profit > 0]
    strategies.sort(
        key=lambda x: x.counter.total_profit * x.counter.profitable_trades / x.counter.total_trades,
        reverse=True,
    )

    print_strategies_performance(strategies)

    save_strategies(
        strategies,
        None if not new_strategies_file_name else f"{settings.FILE_PREFIX}_{new_strategies_file_name}",
    )
