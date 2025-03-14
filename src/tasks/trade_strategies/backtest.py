import warnings
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from pathos.multiprocessing import ProcessingPool as Pool
from pydantic import BaseModel

from services.ta import Figure, dump_strategies_in_file, get_indicators, get_strategies
from services.ta.indicators.models import Panel, Plot, Plots
from services.ta.strategies.models import ComposeStrategiesListMethod, Strategy
from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)


log = get_logger()


class Order(BaseModel):
    buy_price: float
    buy_datetime: Any

    take_profit_price: float
    stop_loss_price: float

    signal_confirmation_time: datetime

    sell_price: float | None = None
    sell_datetime: Any | None = None

    def sell(self, sell_price: float, sell_datetime: datetime, instrument_type: str) -> float:
        self.sell_price = sell_price
        self.sell_datetime = sell_datetime

        profit = self.sell_price - self.buy_price
        profit = profit if instrument_type == "LONG" else -profit
        profit -= self.buy_price * 0.01 * 0.03  # Spread

        return profit


class Wallet(BaseModel):
    LONG: Order | None = None
    SHORT: Order | None = None

    def get(self, direction: str) -> Order | None:
        return self.LONG if direction == "LONG" else self.SHORT

    def set(self, direction: str, order: Order | None) -> None:
        if direction == "LONG":
            self.LONG = order
        else:
            self.SHORT = order


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
            ["00:00", settings.TRADING_START.strftime("%H:%M")],
            [settings.TRADING_END.strftime("%H:%M"), "23:59"],
        ):
            data.loc[data.between_time(non_trading_time[0], non_trading_time[1]).index, column] = np.nan


def _consider_trading_logic(data: pd.DataFrame, strategy: Strategy, settings) -> None:
    wallet = Wallet()

    target_profit = settings.TRADING_TAKE_PROFIT / settings.MULTIPLIER
    stop_loss = settings.TRADING_STOP_LOSS / settings.MULTIPLIER
    stop_loss_confirmation_counter = 0

    for i, row in data[["Close", "LONG", "SHORT", "EXIT"]].iterrows():
        profit = None
        timestamp: datetime = i.to_pydatetime()  # type: ignore

        for tested_direction, opposite_direction in [("LONG", "SHORT"), ("SHORT", "LONG")]:
            tested_instrument = wallet.get(tested_direction)
            opposite_instrument = wallet.get(opposite_direction)

            tested_direction_price: float = row[tested_direction]  # type: ignore
            close_price = row["Close"]
            direction_correction = 1 if tested_direction == "LONG" else -1

            # Buy signal without open positions
            if (
                tested_instrument is None
                and tested_direction_price > 0
                and np.isnan(row["EXIT"])
                and np.isnan(row[opposite_direction])
            ):
                wallet.set(
                    tested_direction,
                    Order(
                        buy_price=tested_direction_price,
                        buy_datetime=timestamp,
                        take_profit_price=tested_direction_price * (1 + (direction_correction * target_profit)),
                        stop_loss_price=tested_direction_price * (1 - (direction_correction * stop_loss)),
                        signal_confirmation_time=timestamp,
                    ),
                )

                if opposite_instrument is not None:
                    profit = opposite_instrument.sell(tested_direction_price, timestamp, opposite_direction)
                    wallet.set(opposite_direction, None)

            if tested_instrument is None:
                continue

            # Exit signal
            if row["EXIT"] > 0:
                sell_price = row["EXIT"]
                profit = tested_instrument.sell(sell_price, timestamp, tested_direction)
                wallet.set(tested_direction, None)

            # Take profit
            if (tested_direction == "LONG" and close_price > tested_instrument.take_profit_price) or (
                tested_direction == "SHORT" and close_price < tested_instrument.take_profit_price
            ):
                sell_price = tested_instrument.take_profit_price
                profit = tested_instrument.sell(sell_price, timestamp, tested_direction)
                wallet.set(tested_direction, None)

            # Stop loss
            if (tested_direction == "LONG" and close_price < tested_instrument.stop_loss_price) or (
                tested_direction == "SHORT" and close_price > tested_instrument.stop_loss_price
            ):
                stop_loss_confirmation_counter += 1

                if stop_loss_confirmation_counter > settings.TRADING_STOP_LOSS_CONFIRMATION_COUNT_MIN:
                    sell_price = close_price
                    profit = tested_instrument.sell(sell_price, timestamp, tested_direction)
                    wallet.set(tested_direction, None)
            else:
                stop_loss_confirmation_counter = 0

            # End of day
            if timestamp.time() >= settings.TRADING_END:
                sell_price = close_price
                profit = tested_instrument.sell(sell_price, timestamp, tested_direction)
                wallet.set(tested_direction, None)

        if profit is not None:
            strategy.counter.total_trades += 1
            strategy.counter.total_profit += profit
            strategy.counter.profitable_trades += 1 if profit > 0 else 0


def process_strategy(kwargs: dict) -> Strategy:
    data: pd.DataFrame = kwargs["data"]
    strategy: Strategy = kwargs["strategy"]
    settings = kwargs["settings"]
    strategy_rank: str | None = kwargs.get("strategy_rank")

    for column in ["LONG", "SHORT", "EXIT"]:
        data[column] = data["Close"]

    _consider_signals(data, strategy, settings)
    _consider_trading_logic(data, strategy, settings)

    log.debug(
        f"Strategy{strategy_rank if strategy_rank else ''}: {strategy.name} ({round(strategy.counter.total_profit)})",
    )

    return strategy


def print_strategies_performance(strategies: list[Strategy]) -> None:
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
def backtest_trade_strategies(
    data: pd.DataFrame,
    compose_strategies_list_method: ComposeStrategiesListMethod,
    settings,
    indicators_filter: list[str] | None = None,
    strategies_file_name_suffix_old: str | None = None,
    strategies_file_name_suffix_new: str | None = None,
    plot: bool = False,
    **kwargs,
) -> None:
    strategies_file_name_prefix = settings.NAME

    indicators_mapping = get_indicators(data, settings, **kwargs)

    strategies = get_strategies(
        compose_strategies_list_method,
        indicators_mapping,
        strategies_file_name_prefix,
        strategies_file_name_suffix_old,
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
        key=lambda x: (x.counter.total_profit / 2) * (x.counter.profitable_trades / x.counter.total_trades),
        reverse=True,
    )

    print_strategies_performance(strategies)

    dump_strategies_in_file(strategies, strategies_file_name_prefix, strategies_file_name_suffix_new)
