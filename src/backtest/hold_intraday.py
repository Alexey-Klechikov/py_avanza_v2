import warnings
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

from services.hold.models import Direction, HoldRule
from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

log = get_logger()


@dataclass
class CutOffResult:
    total: float
    efficiency: float
    cut_off: int
    take_profit: float


@dataclass
class TimePoint:
    weight: float
    take_profit: float
    efficiency: float


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


def _calculate_result(
    data: pd.DataFrame,
    direction: Direction,
    cut_off: int,
    omx_reference_price: int,
) -> Optional[CutOffResult]:
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
    if efficiency < 0.55 or total <= 40:
        return

    return CutOffResult(
        total=round(total, 2),
        efficiency=efficiency,
        cut_off=cut_off,
        take_profit=round(20 * cut_off / omx_reference_price, 2),
    )


def _sort_intervals(
    intervals: Dict[Tuple[time, time], List[CutOffResult]],
) -> List[Tuple[Tuple[time, time], CutOffResult]]:
    return [
        (interval, sorted(cut_off_result, key=lambda x: x.total * x.efficiency, reverse=True)[0])
        for interval, cut_off_result in intervals.items()
        if cut_off_result
    ]


def _split_intervals_to_4_min_time_points(
    intervals: List[Tuple[Tuple[time, time], CutOffResult]],
) -> List[Tuple[time, TimePoint]]:
    time_points = {}
    for interval in intervals:
        start_time, end_time = interval[0]
        interval_duration = (end_time.hour - start_time.hour) * 60 + end_time.minute - start_time.minute
        weight = interval[1].total / interval_duration

        for drift in range(0, interval_duration, 4):
            time_point = (datetime.combine(date.today(), start_time) + timedelta(minutes=drift)).time()
            if time_point in time_points and time_points[time_point].weight > weight:
                continue

            time_points[time_point] = TimePoint(
                weight=round(weight, 2),
                take_profit=interval[1].take_profit,
                efficiency=interval[1].efficiency,
            )

    return sorted([(k, v) for k, v in time_points.items()], key=lambda x: x[0])


def _aggregate_time_points_to_rules(direction: Direction, time_points: List[Tuple[time, TimePoint]]) -> List[HoldRule]:
    hold_rules = []

    current_hold_rule_kwargs = {}
    take_profit_counter = defaultdict(int)
    for t, time_point in time_points:
        take_profit_counter[time_point.take_profit] += 1

        if not current_hold_rule_kwargs:
            current_hold_rule_kwargs.update(
                {
                    "orderbook_direction": direction,
                    "buy_time": t,
                    "sell_time": t,
                    "take_profit": time_point.take_profit,
                    "settings": None,
                },
            )
            continue

        if (t.hour - current_hold_rule_kwargs["sell_time"].hour) * 60 + t.minute - current_hold_rule_kwargs[
            "sell_time"
        ].minute == 4:
            current_hold_rule_kwargs["sell_time"] = t

        else:
            hold_rules.append(HoldRule(**current_hold_rule_kwargs))
            take_profit_counter = defaultdict(int)
            take_profit_counter[time_point.take_profit] += 1

            current_hold_rule_kwargs = {
                "orderbook_direction": direction,
                "buy_time": t,
                "sell_time": t,
                "take_profit": time_point.take_profit,
                "settings": None,
            }

        current_hold_rule_kwargs["take_profit"] = round(
            sorted(
                [(k, v) for k, v in take_profit_counter.items() if v == max(take_profit_counter.values())],
                key=lambda x: x[0],
                reverse=True,
            )[0][0]
            - 0.01,
            2,
        )

    hold_rules.append(HoldRule(**current_hold_rule_kwargs))

    return hold_rules


# MAIN
def backtest_hold_intraday(
    data: pd.DataFrame,
    times: List[Tuple[time, time]],
    direction: Direction,
    omx_reference_price: int,
):
    intervals: Dict[Tuple[time, time], List[CutOffResult]] = {}
    for buy_time, sell_time in times:
        intervals[(buy_time, sell_time)] = []

        data_aggregated_by_time = _aggregate_data_by_time(data, buy_time, sell_time)

        for cut_off in range(5, 30, 2):
            result_per_cut_off = _calculate_result(data_aggregated_by_time, direction, cut_off, omx_reference_price)
            if not result_per_cut_off:
                continue

            intervals[(buy_time, sell_time)].append(result_per_cut_off)

    sorted_intervals = _sort_intervals(intervals)
    time_points = _split_intervals_to_4_min_time_points(sorted_intervals)
    rules = _aggregate_time_points_to_rules(direction, time_points)

    return rules
