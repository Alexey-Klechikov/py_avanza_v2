import warnings
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd
from pathos.multiprocessing import ProcessingPool as Pool

from hold_correlation.models import Correlation, HoldRuleCorrelation, Interval
from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

log = get_logger()


@dataclass
class IntervalsCorrelationQualitative:
    deciding_interval: Interval
    action_interval: Interval
    correlation: Correlation
    efficiency: float

    def __str__(self):
        return f"{self.deciding_interval} ---> {self.action_interval}, corr. {self.correlation}, eff. {self.efficiency}"


@dataclass
class IntervalsCorrelationQuantitative:
    deciding_interval: Interval
    action_interval: Interval
    correlation: Correlation
    counter_profit: float
    counter_deals: int
    efficiency: float
    multiplier: float

    def __str__(self):
        return (
            f"{self.deciding_interval} ---> {self.action_interval}, "
            + f"corr. {self.correlation}, profit. {self.counter_profit}, "
            + f"deals {self.counter_deals}, mult. {self.multiplier},  eff. {self.efficiency})"
        )


def aggregate_data_by_time(
    data: pd.DataFrame,
    slice_duration: int,
) -> pd.DataFrame:
    resampled_data = data.resample(f"{slice_duration}min")
    return pd.DataFrame(
        {
            "Open": resampled_data["Open"].first(),
            "Close": resampled_data["Close"].last(),
            "High": resampled_data["Close"].max(),
            "Low": resampled_data["Close"].min(),
        },
    ).dropna()


def generate_intervals(
    slice_duration: int,
    start: str,
    end: str,
) -> List[Interval]:
    times = [i.time() for i in pd.date_range(start=start, end=end, freq=f"{slice_duration}min")]
    intervals = [Interval(buy_time, sell_time) for buy_time in times for sell_time in times if buy_time < sell_time]
    return intervals


def _get_interval_price_diff(
    interval: Interval,
    data: pd.DataFrame,
) -> float:
    tested_interval_rows = data.between_time(interval.start, interval.end)
    return tested_interval_rows["Close"].iloc[-2] - tested_interval_rows["Open"].iloc[0]


def backtest_intervals_correlation_qualitatively(
    intervals: List[Interval],
    data: pd.DataFrame,
    max_interval_duration: int,
) -> List[Dict[Tuple[Interval, Interval], Dict[Correlation, int]]]:
    log.info("Get intervals correlation efficiency (qualitative)")

    def _backtest_deciding_interval(kwargs: dict) -> Dict[Tuple[Interval, Interval], Dict[Correlation, int]]:
        data: pd.DataFrame = kwargs["data"]
        deciding_interval: Interval = kwargs["deciding_interval"]
        intervals: List[Interval] = kwargs["intervals"]

        deciding_interval_correlations = defaultdict(lambda: {Correlation.SAME: 0, Correlation.OPPOSITE: 0})
        for tested_interval in intervals:
            if any(
                [
                    deciding_interval.start >= tested_interval.start,
                    deciding_interval.start <= tested_interval.start and tested_interval.start <= deciding_interval.end,
                    deciding_interval.start <= tested_interval.end and tested_interval.end <= deciding_interval.end,
                    tested_interval.duration_min() <= 10 or tested_interval.duration_min() >= 3 * 60,
                ],
            ):
                continue

            for _, day_data in data.groupby(data.index.date):  # type: ignore
                try:
                    deciding_interval_price_difference = _get_interval_price_diff(deciding_interval, day_data)
                    tested_interval_price_difference = _get_interval_price_diff(tested_interval, day_data)
                except IndexError:
                    continue

                if abs(deciding_interval_price_difference) < 2:
                    continue

                deciding_interval_correlations[(deciding_interval, tested_interval)][
                    Correlation(
                        (
                            "SAME"
                            if (deciding_interval_price_difference * tested_interval_price_difference) > 0
                            else "OPPOSITE"
                        ),
                    )
                ] += 1

        return deciding_interval_correlations

    with Pool() as pool:
        intervals_correlation = list(
            pool.map(
                _backtest_deciding_interval,
                [
                    {
                        "data": data,
                        "deciding_interval": deciding_interval,
                        "intervals": intervals,
                    }
                    for deciding_interval in intervals
                    if deciding_interval.duration_min() <= max_interval_duration
                ],
            ),
        )

    return [i for i in intervals_correlation if i]


def aggregate_intervals_correlations(
    intervals_correlation: List[Dict[Tuple[Interval, Interval], Dict[Correlation, int]]],
    min_efficiency: float,
) -> List[IntervalsCorrelationQualitative]:
    log.info("Aggregate intervals correlation results")

    correlated_intervals = []
    for results_per_deciding_interval in intervals_correlation:
        for (deciding_interval, action_interval), backtest_result in results_per_deciding_interval.items():
            total = sum(backtest_result.values())

            for correlation, counter in backtest_result.items():
                correlated_intervals.append(
                    IntervalsCorrelationQualitative(
                        deciding_interval,
                        action_interval,
                        correlation,
                        round(counter / total, 2),
                    ),
                )

    correlated_intervals = [i for i in correlated_intervals if i.efficiency > min_efficiency]
    correlated_intervals = sorted(correlated_intervals, key=lambda x: x.efficiency, reverse=True)

    return correlated_intervals


def backtest_intervals_correlation_quantitatively(
    aggregated_intervals_correlation: List[IntervalsCorrelationQualitative],
    resampled_data: pd.DataFrame,
    min_deciding_price_change: float,
    max_counter_cut_off: float,
    max_cut_off_multiplier: int,
    min_efficiency: float,
) -> List[IntervalsCorrelationQuantitative]:
    log.info("Get intervals correlation efficiency (quantitative)")

    def _backtest_intervals_correlation(kwargs: dict) -> Optional[IntervalsCorrelationQuantitative]:
        deciding_interval: Interval = kwargs["deciding_interval"]
        action_interval: Interval = kwargs["action_interval"]
        correlation: Correlation = kwargs["correlation"]

        stats = []
        for _, day_data in resampled_data.groupby(resampled_data.index.date):  # type: ignore
            try:
                stat = (
                    _get_interval_price_diff(deciding_interval, day_data),
                    _get_interval_price_diff(action_interval, day_data)
                    * (-1 if correlation == Correlation.OPPOSITE else 1),
                )
            except IndexError:
                continue

            if abs(stat[0]) < min_deciding_price_change:
                continue

            stats.append(stat)

        if not stats:
            return

        stats_per_cut_off = []
        for cut_off_multiplier in [i / 10 for i in range(10, max_cut_off_multiplier)]:
            counter_per_cut_off = IntervalsCorrelationQuantitative(
                counter_profit=0,
                counter_deals=len(stats),
                multiplier=cut_off_multiplier,
                efficiency=0,
                deciding_interval=deciding_interval,
                action_interval=action_interval,
                correlation=correlation,
            )
            for stat in stats:
                if (stat[0] > 0 and stat[1] > 0) or (stat[0] < 0 and stat[1] < 0):
                    if abs(stat[0] * cut_off_multiplier) < abs(stat[1]):
                        counter_per_cut_off.counter_profit += abs(stat[0] * cut_off_multiplier)
                        counter_per_cut_off.efficiency += 1
                else:
                    counter_per_cut_off.counter_profit -= abs(stat[1])

            counter_per_cut_off.efficiency = round(counter_per_cut_off.efficiency / len(stats), 2)
            if (
                counter_per_cut_off.counter_profit < max_counter_cut_off
                or counter_per_cut_off.efficiency < min_efficiency
            ):
                continue

            counter_per_cut_off.counter_profit = round(counter_per_cut_off.counter_profit, 2)
            stats_per_cut_off.append(counter_per_cut_off)

        if not stats_per_cut_off:
            return

        return max(stats_per_cut_off, key=lambda x: x.counter_profit * x.efficiency)

    with Pool() as pool:
        intervals_correlation_efficiency = list(
            pool.map(
                _backtest_intervals_correlation,
                [
                    {
                        "deciding_interval": i.deciding_interval,
                        "action_interval": i.action_interval,
                        "correlation": i.correlation,
                    }
                    for i in aggregated_intervals_correlation
                ],
            ),
        )

    intervals_correlation_efficiency = sorted(
        [i for i in intervals_correlation_efficiency if i],
        key=lambda x: x.counter_profit * x.efficiency,
        reverse=True,
    )

    return intervals_correlation_efficiency


def filter_intervals_correlations(
    intervals_correlation_efficiency_quantitative: List[IntervalsCorrelationQuantitative],
) -> List[IntervalsCorrelationQuantitative]:
    log.info("Filter intervals correlation results")

    reshaped_intervals_correlation = defaultdict(list)
    for interval_correlation in intervals_correlation_efficiency_quantitative:
        reshaped_intervals_correlation[interval_correlation.deciding_interval].append(interval_correlation)

    filtered_intervals_correlation: List[IntervalsCorrelationQuantitative] = []
    for interval_correlations in reshaped_intervals_correlation.values():
        max_efficiency_interval_correlation = max(interval_correlations, key=lambda x: x.counter_profit * x.efficiency)
        top_efficiency_interval_correlations = [
            i
            for i in interval_correlations
            if (i.counter_profit * i.efficiency)
            >= (max_efficiency_interval_correlation.counter_profit * max_efficiency_interval_correlation.efficiency * 0.9)
        ]
        shortest_duration_top_efficiency_interval_correlation = min(
            top_efficiency_interval_correlations,
            key=lambda x: x.action_interval.duration_min(),
        )
        filtered_intervals_correlation.append(shortest_duration_top_efficiency_interval_correlation)

    return filtered_intervals_correlation


# MAIN
def backtest_hold_intraday_correlation(settings, data: pd.DataFrame, slice_duration: int) -> List[HoldRuleCorrelation]:
    resampled_data = aggregate_data_by_time(data, slice_duration)
    intervals = generate_intervals(
        slice_duration,
        start="09:00",
        end="17:00",
    )

    intervals_correlation_efficiency_qualitative = backtest_intervals_correlation_qualitatively(
        intervals,
        resampled_data,
        max_interval_duration=60 * 2,
    )
    aggregated_intervals_correlation = aggregate_intervals_correlations(
        intervals_correlation_efficiency_qualitative,
        min_efficiency=0.75,
    )
    intervals_correlation_efficiency_quantitative = backtest_intervals_correlation_quantitatively(
        aggregated_intervals_correlation,
        resampled_data,
        min_deciding_price_change=settings.MIN_DECIDING_PRICE_CHANGE,
        max_counter_cut_off=10.0,
        max_cut_off_multiplier=25,
        min_efficiency=0.70,
    )
    filtered_intervals_correlation = filter_intervals_correlations(intervals_correlation_efficiency_quantitative)

    return [
        HoldRuleCorrelation(
            deciding_interval=i.deciding_interval,
            action_interval=i.action_interval,
            correlation=i.correlation,
            efficiency=i.efficiency,
            multiplier=i.multiplier,
        )
        for i in filtered_intervals_correlation
    ]
