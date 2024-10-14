import warnings
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional

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


def _aggregate_data_by_time(data: pd.DataFrame, end_od_day: time, close_time: time) -> pd.DataFrame:
    data.index = pd.to_datetime(data.index)
    data_daily = data.resample("D")

    data_aggregated_by_time = pd.DataFrame(
        {
            "Top price before close_time": data_daily["Close"].apply(lambda x: x[x.index.time < close_time].max()),
            "Low price before close_time": data_daily["Close"].apply(lambda x: x[x.index.time < close_time].min()),
            "End price at close_time": data_daily["Close"].apply(lambda x: x.at_time(close_time)),
            "Price at end_od_day": data_daily["Close"].apply(lambda x: x.at_time(end_od_day)),
        },
    )

    data_aggregated_by_time.index = pd.to_datetime(data_aggregated_by_time.index)
    data_aggregated_by_time_grouped = data_aggregated_by_time.groupby(data_aggregated_by_time.index.date)
    data_aggregated_by_time = data_aggregated_by_time_grouped.agg(
        {
            "Top price before close_time": "first",
            "Low price before close_time": "first",
            "End price at close_time": "first",
            "Price at end_od_day": "last",
        },
    ).dropna()

    # log.debug(f"Data aggregated by time: {data_aggregated_by_time}")

    return data_aggregated_by_time


def _calculate_gaps(data: pd.DataFrame) -> dict:
    gaps = {}

    for i, (index, row) in enumerate(data.iterrows()):
        if i == 0:
            continue

        gaps[index] = {
            "high": row["Top price before close_time"] - data.iloc[i - 1]["Price at end_od_day"],
            "low": row["Low price before close_time"] - data.iloc[i - 1]["Price at end_od_day"],
            "close": row["End price at close_time"] - data.iloc[i - 1]["Price at end_od_day"],
        }

    # log.debug(f"Gaps: {gaps}")

    return gaps


def _calculate_result(gaps: dict, direction: Direction, cut_off: int, omx_reference_price: int) -> dict:
    counter = 0
    total = 0
    for gap in gaps.values():
        if (gap["high"] if direction == Direction.BULL else (gap["low"] * -1)) > cut_off:
            total += cut_off
            counter += 1
        else:
            profit = gap["close"] * (1 if direction == Direction.BULL else -1)
            total += profit
            if profit > 0:
                counter += 1

    return {
        "efficiency": 0.0 if not gaps else round(counter / len(gaps), 2),
        "total": round(total, 2),
        "take_profit": round(20 * cut_off / omx_reference_price, 2),
    }


def _get_top_hold_rule(intervals: Dict[IntervalTime, dict]) -> Optional[dict]:
    hold_rule_kwargs: Optional[dict] = {}
    for interval, results_for_interval in intervals.items():
        top_total = sorted(results_for_interval.values(), key=lambda x: x["total"], reverse=True)[0]["total"]
        filtered_rules = [i for i in results_for_interval.values() if i["total"] >= top_total * 0.8]
        if not filtered_rules:
            continue

        log.debug(f"Interval: {interval}. Top total: {top_total}. Selected rule: {filtered_rules[0]}")

        if not hold_rule_kwargs or (
            filtered_rules[0]["total"] * filtered_rules[0]["efficiency"]
            > hold_rule_kwargs.get("total", 0) * hold_rule_kwargs.get("efficiency", 0)
        ):
            hold_rule_kwargs = {**filtered_rules[0], "end_od_day": interval.start, "close_time": interval.end}

    return hold_rule_kwargs


# MAIN
def backtest_hold_interday(
    data: pd.DataFrame,
    end_od_day_times: List[time],
    close_times: List[time],
    direction: Direction,
    omx_reference_price: int,
) -> HoldRule:
    intervals: Dict[IntervalTime, dict] = defaultdict(dict)
    for end_od_day in end_od_day_times:
        for close_time in close_times:
            data_aggregated_by_time = _aggregate_data_by_time(data, end_od_day, close_time)
            gaps = _calculate_gaps(data_aggregated_by_time)

            results_per_cut_off = {}
            for cut_off in range(10, 40, 2):
                results_per_cut_off[cut_off] = _calculate_result(gaps, direction, cut_off, omx_reference_price)

            intervals[
                IntervalTime(
                    (datetime.combine(datetime.today(), end_od_day) + timedelta(minutes=2)).time(),
                    (datetime.combine(datetime.today(), close_time) + timedelta(minutes=2)).time(),
                )
            ] = results_per_cut_off

    hold_rule_kwargs = _get_top_hold_rule(intervals)

    if not hold_rule_kwargs:
        raise Exception("No hold rule found")

    return HoldRule(
        orderbook_direction=direction,
        buy_time=hold_rule_kwargs["end_od_day"],
        sell_time=hold_rule_kwargs["close_time"],
        take_profit=hold_rule_kwargs["take_profit"] - 0.01,
        settings=None,
    )
