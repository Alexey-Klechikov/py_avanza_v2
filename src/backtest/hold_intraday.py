import warnings
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

from services.hold.models import Direction, HoldRule
from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

log = get_logger()


@dataclass(frozen=True)
class IntervalTime:
    start: time
    end: time

    def __str__(self) -> str:
        return f"{self.start.strftime('%H:%M')} - {self.end.strftime('%H:%M')}"


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
            "high": daily_data["Close"].apply(
                lambda x: x[(x.index.time >= buy_time) & (x.index.time <= sell_time)].max(),
            ),
            "low": daily_data["Close"].apply(
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
    if efficiency <= 0.67 or total <= 40:
        return

    return CutOffResult(
        total=round(total, 2),
        efficiency=efficiency,
        cut_off=cut_off,
        take_profit=round(20 * cut_off / omx_reference_price, 2),
    )


def _sort_intervals(
    intervals: Dict[IntervalTime, List[CutOffResult]],
) -> List[Tuple[IntervalTime, CutOffResult]]:
    return [
        (interval, sorted(cut_off_result, key=lambda x: x.total * x.efficiency, reverse=True)[0])
        for interval, cut_off_result in intervals.items()
        if cut_off_result
    ]


def _generate_rules(sorted_intervals: List[Tuple[IntervalTime, CutOffResult]], direction: Direction) -> List[HoldRule]:
    rules = []

    while sorted_intervals:
        max_efficiency_interval = max(sorted_intervals, key=lambda x: x[1].efficiency)
        log.debug(
            "Max efficiency interval: {}, {}".format(
                max_efficiency_interval[0],
                max_efficiency_interval[1],
            ),
        )

        not_assigned_intervals = []
        rule_extension_candidates = []
        for interval in sorted_intervals:
            if interval[0].start == max_efficiency_interval[0].start:
                rule_extension_candidates.append(interval)
                continue
            elif any(
                [
                    interval[0].start <= max_efficiency_interval[0].start <= interval[0].end,
                    interval[0].start <= max_efficiency_interval[0].end <= interval[0].end,
                    max_efficiency_interval[0].start <= interval[0].start <= max_efficiency_interval[0].end,
                ],
            ):
                continue

            not_assigned_intervals.append(interval)

        rule = HoldRule(
            orderbook_direction=direction,
            buy_time=max_efficiency_interval[0].start,
            sell_time=max_efficiency_interval[0].end,
            take_profit=max_efficiency_interval[1].take_profit,
            settings=None,
        )
        for rule_extension_candidate in rule_extension_candidates:
            if all(
                [
                    rule.sell_time <= rule_extension_candidate[0].end,
                    rule.take_profit <= rule_extension_candidate[1].take_profit,
                ],
            ):
                rule.sell_time = rule_extension_candidate[0].end
                log.debug(f"Rule is extended with end time: {rule.sell_time}")
        rules.append(rule)

        sorted_intervals = [i for i in not_assigned_intervals if i[0].start > rule.sell_time]

    return rules


# MAIN
def backtest_hold_intraday(
    data: pd.DataFrame,
    times: List[Tuple[time, time]],
    direction: Direction,
    omx_reference_price: int,
) -> List[HoldRule]:
    log.warn(f"Backtesting intraday hold strategy for {direction}")
    intervals: Dict[IntervalTime, List[CutOffResult]] = defaultdict(list)
    for buy_time, sell_time in times:
        data_aggregated_by_time = _aggregate_data_by_time(data, buy_time, sell_time)

        for cut_off in range(5, 30, 2):
            result_per_cut_off = _calculate_result(data_aggregated_by_time, direction, cut_off, omx_reference_price)
            if not result_per_cut_off:
                continue

            intervals[
                IntervalTime(
                    (datetime.combine(datetime.today(), buy_time) + timedelta(minutes=2)).time(),
                    (datetime.combine(datetime.today(), sell_time) + timedelta(minutes=2)).time(),
                )
            ].append(result_per_cut_off)

    sorted_intervals = _sort_intervals(intervals)
    rules = _generate_rules(sorted_intervals, direction)

    return rules
