import warnings
from copy import deepcopy

import pandas as pd
import talib
from pathos.multiprocessing import ProcessingPool as Pool

from apis.avanza.trade.models import Direction
from trade_candlesticks.models import CandlestickPatternRule, Deal
from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

log = get_logger()


def extend_data_with_candlestick_pattern_column(data: pd.DataFrame):
    log.info("Extending data with candlestick patterns columns")

    for candlestick_pattern_name in talib.get_function_groups()["Pattern Recognition"]:
        candlestick_pattern_method = getattr(talib, candlestick_pattern_name)
        candlestick_pattern_column = candlestick_pattern_method(data["Open"], data["High"], data["Low"], data["Close"])

        value_statistics = candlestick_pattern_column.value_counts().to_dict()
        value_statistics = {i: value_statistics[i] for i in value_statistics if i not in [0, -200, 200]}

        if value_statistics and sum(value_statistics.values()) > 4:
            log.debug(f"Pattern: {candlestick_pattern_name} | Stats: {value_statistics}")
            data[candlestick_pattern_name] = candlestick_pattern_column

        else:
            log.debug(f"[Not enough data] Pattern: {candlestick_pattern_name} | Stats: {value_statistics}")


def _filter_data(data: pd.DataFrame, column: str, direction: Direction) -> tuple[pd.DataFrame, int]:
    data = data.copy()[["Close", column]]

    value_filter = 100 if direction == Direction.BULL else -100
    data[column] = (data[column] == value_filter).astype(int)

    signals_counter = data[column].sum()
    if signals_counter < 5:
        return pd.DataFrame(), signals_counter

    dates_with_signal = data.index[data[column] == 1].normalize()  # type: ignore
    filtered_data = data[data.index.normalize().isin(dates_with_signal)]  # type: ignore

    return filtered_data, signals_counter


def backtest_candlestick_pattern(kwargs: dict) -> CandlestickPatternRule | None:
    column = kwargs["candlestick_pattern_column"]
    direction = Direction(kwargs["direction"])

    data, signals_counter = _filter_data(kwargs["data"], column, direction)
    if signals_counter < 10:
        return

    candlestick_pattern_variants = [
        CandlestickPatternRule(
            column=column,
            direction=direction,
            take_profit=i,
            stop_loss=j,
        )
        for i in range(3, 10)
        for j in range(3, 8)
        if i >= j
    ]
    for candlestick_pattern_variant in candlestick_pattern_variants:
        bad_signals_counter = 0

        for _, data_day in data.groupby(data.index.date):  # type: ignore
            deal = Deal()
            for _, row in data_day.iterrows():
                if row[candlestick_pattern_variant.column] == 1:
                    if not deal.buy_price:
                        deal.buy_time = row.name

                    deal.buy_price = row["Close"]
                    continue

                if not deal.buy_price:
                    continue

                current_price_change = (row["Close"] - deal.buy_price) * (
                    1 if candlestick_pattern_variant.direction == Direction.BULL else -1
                )

                if (
                    current_price_change > candlestick_pattern_variant.take_profit
                    or current_price_change < -candlestick_pattern_variant.stop_loss
                    or row.name.time() > pd.to_datetime("17:10").time()
                ):
                    deal.sell_price = row["Close"]
                    deal.profit = current_price_change
                    deal.duration = round((row.name - deal.buy_time).total_seconds() / 60)

                    if deal.profit < 0:
                        bad_signals_counter += 1

                    candlestick_pattern_variant.deals.append(deepcopy(deal))
                    deal = Deal()

            if bad_signals_counter > signals_counter * 0.5:
                break

        candlestick_pattern_variant.aggregate_values_from_deals()

    top_candlestick_pattern_variant = max(candlestick_pattern_variants, key=lambda x: x.profit * x.efficiency)
    if (
        not top_candlestick_pattern_variant
        or top_candlestick_pattern_variant.profit <= 0
        or top_candlestick_pattern_variant.efficiency <= 0.5
    ):
        return

    log.debug(top_candlestick_pattern_variant)

    return top_candlestick_pattern_variant


# MAIN
def backtest_trade_candlesticks(data: pd.DataFrame) -> list[CandlestickPatternRule]:
    extend_data_with_candlestick_pattern_column(data)

    with Pool() as pool:
        candlestick_patterns_rules = list(
            pool.map(
                backtest_candlestick_pattern,
                [
                    {
                        "data": data,
                        "candlestick_pattern_column": candlestick_pattern_column,
                        "direction": direction,
                    }
                    for candlestick_pattern_column in data.columns
                    if candlestick_pattern_column.startswith("CDL")
                    for direction in ["BULL", "BEAR"]
                ],
            ),
        )

    return sorted(
        [i for i in candlestick_patterns_rules if i and i.profit and i.profit > 0],
        key=lambda x: x.profit * x.efficiency,
        reverse=True,
    )
