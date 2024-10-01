import warnings
from datetime import time
from typing import List, Optional, Tuple

import pandas as pd

from services.hold.models import Direction
from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

log = get_logger()


def _aggregate_data_by_time(data: pd.DataFrame, buy_time: time, sell_time: time) -> pd.DataFrame:
    daily_data = data.resample("D")

    data_aggregated_by_time = pd.DataFrame(
        {
            "buy": daily_data["Close"].apply(lambda x: x.at_time(buy_time)),
            "sell": daily_data["Close"].apply(lambda x: x.at_time(sell_time)),
            "high": daily_data["High"].apply(
                lambda x: x[(x.index.time >= buy_time) & (x.index.time <= sell_time)].max(),
            ),
            "low": daily_data["Low"].apply(
                lambda x: x[(x.index.time >= buy_time) & (x.index.time <= sell_time)].min(),
            ),
        },
    )
    data_aggregated_by_time.index = pd.to_datetime(data_aggregated_by_time.index)
    data_aggregated_by_time_grouped = data_aggregated_by_time.groupby(data_aggregated_by_time.index.date)

    data_aggregated_by_time = data_aggregated_by_time_grouped.agg(
        {
            "buy": "first",
            "sell": "first",
            "high": "first",
            "low": "first",
        },
    ).dropna()

    return data_aggregated_by_time


def _calculate_result(data: pd.DataFrame, direction: Direction, cut_off: int, omx_reference_price: int) -> Optional[dict]:
    counter_profitable_trade = 0
    total = 0
    for _, row in data.iterrows():
        if (direction == Direction.BULL and (row["high"] - row["buy"] > cut_off)) or (
            direction == Direction.BEAR and (row["buy"] - row["low"] > cut_off)
        ):
            profit = cut_off

        else:
            profit = (row["sell"] - row["buy"]) * (1 if direction == Direction.BULL else -1)
            total += profit

        if profit > 0:
            counter_profitable_trade += 1

    efficiency = 0.0 if data.shape[0] == 0 else round(counter_profitable_trade / data.shape[0], 2)
    if efficiency < 0.55 or total <= 0:
        return

    return {
        "total": round(total, 2),
        "efficiency": efficiency,
        "cut_off": cut_off,
        "take_profit": round(20 * cut_off / omx_reference_price, 2),
    }


def _sort_results(result_for_intervals: dict) -> List[Tuple[Tuple[time, time], dict]]:
    reformed_results = [
        (interval, sorted(efficiencies, key=lambda x: x["total"] * x["efficiency"], reverse=True)[0])
        for interval, efficiencies in result_for_intervals.items()
        if efficiencies
    ]

    return sorted(reformed_results, key=lambda x: x[1]["total"] * x[1]["efficiency"], reverse=True)


# MAIN
def backtest_hold_intraday(
    data: pd.DataFrame,
    times: List[Tuple[time, time]],
    direction: Direction,
    omx_reference_price: int,
) -> list:
    result_for_intervals = {}
    for buy_time, sell_time in times:
        result_for_intervals[(buy_time, sell_time)] = []

        data_aggregated_by_time = _aggregate_data_by_time(data, buy_time, sell_time)

        for cut_off in range(5, 50, 2):
            result_per_cut_off = _calculate_result(data_aggregated_by_time, direction, cut_off, omx_reference_price)
            if not result_per_cut_off:
                continue

            result_for_intervals[(buy_time, sell_time)].append(result_per_cut_off)

    return _sort_results(result_for_intervals)
