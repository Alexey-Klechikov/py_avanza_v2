import warnings
from copy import deepcopy

import pandas as pd

from apis.avanza.trade.models import Direction
from services.candlesticks import append_candlestick_patterns
from tasks.trade_candlesticks.models import CandlestickPatternRule, Deal
from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

log = get_logger()


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
    column = kwargs["pattern_column"]
    direction = Direction(kwargs["direction"])

    data, signals_counter = _filter_data(kwargs["data"], column, direction)
    if signals_counter < 10:
        return

    pattern_variants = [
        CandlestickPatternRule(
            column=column,
            direction=direction,
            take_profit=i,
            stop_loss=j,
        )
        for i in range(4, 10)
        for j in range(4, 8)
        if i >= j
    ]
    for pattern_variant in pattern_variants:
        bad_signals_counter = 0

        for _, data_day in data.groupby(data.index.date):  # type: ignore
            deal = Deal()
            for _, row in data_day.iterrows():
                if not deal.buy_price:
                    if row[pattern_variant.column] == 1:
                        deal.buy_time = row.name
                        deal.buy_price = row["Close"]

                    continue

                if row[pattern_variant.column] == 1:
                    signals_counter -= 1

                if round((row.name - deal.buy_time).total_seconds() / 60) == 2:
                    continue

                current_price_change = (row["Close"] - deal.buy_price) * (
                    1 if pattern_variant.direction == Direction.BULL else -1
                )

                if (
                    current_price_change > pattern_variant.take_profit
                    or current_price_change < -pattern_variant.stop_loss
                    or row.name.time() > pd.to_datetime("17:10").time()
                ):
                    deal.sell_price = row["Close"]
                    deal.profit = current_price_change
                    deal.duration = round((row.name - deal.buy_time).total_seconds() / 60)

                    if deal.profit < 0:
                        bad_signals_counter += 1

                    pattern_variant.deals.append(deepcopy(deal))
                    deal = Deal()

            if bad_signals_counter > signals_counter * 0.5:
                break

        pattern_variant.aggregate_values_from_deals()

    filtered_pattern_variants = [
        i for i in pattern_variants if i.profit > 10 and i.efficiency > 0.54 and len(i.deals) > 8
    ]
    if not filtered_pattern_variants:
        return

    return max(
        filtered_pattern_variants,
        key=lambda x: x.profit * x.efficiency,
    )


# MAIN
def backtest_trade_candlesticks(data: pd.DataFrame) -> list[CandlestickPatternRule]:
    data = data.loc[data.index.time < pd.to_datetime("17:15").time()]  # type: ignore
    data = append_candlestick_patterns(data)

    patterns_rules = []
    for kwargs in [
        {
            "data": data,
            "pattern_column": pattern_column,
            "direction": direction,
        }
        for pattern_column in data.columns
        if pattern_column.startswith("CDL") or pattern_column.startswith("PTN")
        for direction in ["BULL", "BEAR"]
    ]:
        pattern_rule = backtest_candlestick_pattern(kwargs)

        if pattern_rule:
            log.debug(pattern_rule)
            patterns_rules.append(pattern_rule)

    return sorted(
        patterns_rules,
        key=lambda x: x.efficiency,
        reverse=True,
    )
