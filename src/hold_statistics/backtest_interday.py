import warnings
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional

import pandas as pd

from hold_statistics.models import Direction, HoldRuleStatistics
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
class CandidateRule:
    take_profit: float
    efficiency: float
    total: float

    end_of_day: Optional[time] = None
    close_time: Optional[time] = None

    def __str__(self) -> str:
        return f"Total: {self.total}. Take profit: {self.take_profit}. Efficiency: {self.efficiency}."


def _aggregate_data_by_time(data: pd.DataFrame, end_of_day: time, close_time: time) -> pd.DataFrame:
    data.index = pd.to_datetime(data.index)
    data_daily = data.resample("D")

    data_aggregated_by_time = pd.DataFrame(
        {
            "Top price before close_time": data_daily["Close"].apply(lambda x: x[x.index.time < close_time].max()),
            "Low price before close_time": data_daily["Close"].apply(lambda x: x[x.index.time < close_time].min()),
            "End price at close_time": data_daily["Close"].apply(lambda x: x.at_time(close_time)),
            "Price at end_of_day": data_daily["Close"].apply(lambda x: x.at_time(end_of_day)),
        },
    )

    data_aggregated_by_time.index = pd.to_datetime(data_aggregated_by_time.index)
    data_aggregated_by_time_grouped = data_aggregated_by_time.groupby(data_aggregated_by_time.index.date)
    data_aggregated_by_time = data_aggregated_by_time_grouped.agg(
        {
            "Top price before close_time": "first",
            "Low price before close_time": "first",
            "End price at close_time": "first",
            "Price at end_of_day": "last",
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
            "high": row["Top price before close_time"] - data.iloc[i - 1]["Price at end_of_day"],
            "low": row["Low price before close_time"] - data.iloc[i - 1]["Price at end_of_day"],
            "close": row["End price at close_time"] - data.iloc[i - 1]["Price at end_of_day"],
        }

    # log.debug(f"Gaps: {gaps}")

    return gaps


def _calculate_candidate_rule(gaps: dict, direction: Direction, cut_off: int, omx_reference_price: int) -> CandidateRule:
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

    return CandidateRule(
        take_profit=round(20 * cut_off / omx_reference_price, 2),
        efficiency=round(0.0 if not gaps else counter / len(gaps), 2),
        total=round(total, 2),
    )


def _get_hold_rule_from_candidate_rules(
    intervals: Dict[IntervalTime, List[CandidateRule]],
    direction: Direction,
) -> HoldRuleStatistics:
    final_candidate_rule: Optional[CandidateRule] = None
    for interval, candidate_rules in intervals.items():
        top_total = max([i.total for i in candidate_rules])
        filtered_candidate_rules = [i for i in candidate_rules if i.total >= top_total * 0.8]
        if not filtered_candidate_rules:
            continue

        selected_candidate_rule = min(filtered_candidate_rules, key=lambda x: x.total)

        log.debug(f"Interval: {interval}. Top total: {top_total}. {selected_candidate_rule}")

        if not final_candidate_rule or (
            selected_candidate_rule.total * selected_candidate_rule.efficiency
            > final_candidate_rule.total * final_candidate_rule.efficiency
        ):
            final_candidate_rule = selected_candidate_rule
            final_candidate_rule.end_of_day = interval.start
            final_candidate_rule.close_time = interval.end

    if not final_candidate_rule or not final_candidate_rule.end_of_day or not final_candidate_rule.close_time:
        raise Exception("No final candidate rule found")

    return HoldRuleStatistics(
        orderbook_direction=direction,
        buy_time=final_candidate_rule.end_of_day,
        sell_time=final_candidate_rule.close_time,
        take_profit=final_candidate_rule.take_profit - 0.01,
        settings=None,
    )


# MAIN
def backtest_hold_interday_statistics(
    data: pd.DataFrame,
    slice_duration: int,
    direction: Direction,
    omx_reference_price: int,
) -> HoldRuleStatistics:
    eod_times = [i.time() for i in pd.date_range(start="16:50", end="17:16", freq=f"{slice_duration}min")]
    close_times = [i.time() for i in pd.date_range(start="09:02", end="09:58", freq=f"{slice_duration}min")]

    intervals: Dict[IntervalTime, List[CandidateRule]] = defaultdict(list)
    for end_of_day in eod_times:
        for close_time in close_times:
            data_aggregated_by_time = _aggregate_data_by_time(data, end_of_day, close_time)
            gaps = _calculate_gaps(data_aggregated_by_time)

            for cut_off in range(10, 40, 2):
                intervals[
                    IntervalTime(
                        (datetime.combine(datetime.today(), end_of_day) + timedelta(minutes=2)).time(),
                        (datetime.combine(datetime.today(), close_time) + timedelta(minutes=2)).time(),
                    )
                ].append(_calculate_candidate_rule(gaps, direction, cut_off, omx_reference_price))

    return _get_hold_rule_from_candidate_rules(intervals, direction)
