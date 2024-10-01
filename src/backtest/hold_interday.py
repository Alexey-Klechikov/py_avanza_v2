import warnings
from datetime import time

import pandas as pd

from services.hold.models import Direction
from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

log = get_logger()


def _aggregate_data_by_time(data: pd.DataFrame, end_od_day: time, close_time: time) -> pd.DataFrame:
    data.index = pd.to_datetime(data.index)
    data_daily = data.resample("D")

    data_aggregated_by_time = pd.DataFrame(
        {
            "Top price before close_time": data_daily["High"].apply(lambda x: x[x.index.time < close_time].max()),
            "Low price before close_time": data_daily["Low"].apply(lambda x: x[x.index.time < close_time].min()),
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
        "efficiency": round(counter / len(gaps), 2),
        "total": round(total, 2),
        "take_profit": round(20 * cut_off / omx_reference_price, 2),
    }


# MAIN
def backtest_hold_interday(
    data: pd.DataFrame,
    end_od_day: time,
    close_time: time,
    direction: Direction,
    omx_reference_price: int,
) -> dict:
    data_aggregated_by_time = _aggregate_data_by_time(data, end_od_day, close_time)
    gaps = _calculate_gaps(data_aggregated_by_time)

    result = {}
    for cut_off in range(5, 100, 2):
        result[cut_off] = _calculate_result(gaps, direction, cut_off, omx_reference_price)

    return result
