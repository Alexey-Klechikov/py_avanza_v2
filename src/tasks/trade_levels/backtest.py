from copy import copy
from datetime import datetime, time
from pprint import pprint

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema

from tasks.trade_levels.models import Deal
from utils.logger import get_logger

log = get_logger()


class Support:
    def __init__(self, lookback_data: pd.DataFrame, settings):
        self.settings = settings

        self._levels = self._get_levels_support(lookback_data)

        self.last_crossed_level = None

    def _get_levels_support(
        self,
        lookback_data: pd.DataFrame,
        peak_range: int = 3,
        slice_step: int = 1,
        counter_min: int = 5,
    ) -> dict:
        lookback_data["min"] = False
        lookback_data["min"].iloc[
            argrelextrema(
                lookback_data["Close"].values,
                np.less,
                order=peak_range,
            )[0]
        ] = True  # type: ignore

        data_min = lookback_data[lookback_data["min"] is True]["Close"]

        bins_min = np.arange(round(data_min.min()), round(data_min.max()), slice_step)
        counts_min, bin_edges_min = np.histogram(data_min.tolist(), bins=bins_min)

        return {edge: count for edge, count in zip(bin_edges_min, counts_min) if count >= counter_min}

    def get_deals(self, tested_data: pd.DataFrame):
        deals = []

        pprint(self._levels)

        deal = Deal()
        for i, row in tested_data.iterrows():
            current_level = None if not (int(row["ema"]) + 1) in self._levels else int(row["ema"]) + 1

            if current_level and row["ema"] < row["ema_previous"]:
                if self.last_crossed_level == current_level:
                    continue

                self.last_crossed_level = current_level

                print(f"Crossed level: {self.last_crossed_level} at {i}")
                if not deal.buy_price:
                    deal.buy_price = row["Close"]
                    deal.buy_time = i  # type: ignore

            elif (
                self.last_crossed_level
                and int(row["ema"]) > self.last_crossed_level
                and row["ema"] > row["ema_previous"]
                and deal.buy_price
            ):
                deal.sell_price = row["Close"]
                deal.sell_time = i  # type: ignore
                deal.profit = -1 * (deal.sell_price - deal.buy_price)

                log.info(f"Deal: {deal}")

                deals.append(copy(deal))

                deal = Deal()


class Resistance:
    def __init__(self, lookback_data: pd.DataFrame, settings):
        self.settings = settings

        self._levels = self._get_levels_resistance(lookback_data)

    def _get_levels_resistance(
        self,
        lookback_data: pd.DataFrame,
        peak_range: int = 3,
        slice_step: int = 1,
        counter_min: int = 4,
    ) -> dict:
        lookback_data["max"] = False
        lookback_data["max"].iloc[argrelextrema(lookback_data["Close"].values, np.greater, order=peak_range)[0]] = True

        data_max = lookback_data[lookback_data["max"] is True]["Close"]

        bins_max = np.arange(round(data_max.min()), round(data_max.max()), slice_step)
        counts_max, bin_edges_max = np.histogram(data_max.tolist(), bins=bins_max)

        return {edge: count for edge, count in zip(bin_edges_max, counts_max) if count >= counter_min}


def get_lookback_data(data: pd.DataFrame, date: datetime, lookback_days: int) -> pd.DataFrame:
    date_from = np.busday_offset(date, -lookback_days, roll="backward").astype(datetime)

    return data.loc[
        (data.index >= datetime.combine(date_from, time(9, 0))) & (data.index < datetime.combine(date, time(0, 0)))
    ]


def backtest_one_day(tested_data: pd.DataFrame, lookback_data: pd.DataFrame, settings) -> None:
    support = Support(lookback_data, settings)
    support.get_deals(tested_data)

    resistance = Resistance(lookback_data, settings)

    print(resistance)


# MAIN
def backtest_trade_levels(data: pd.DataFrame, settings) -> None:
    data["ema"] = data.ta.ema(length=settings.EMA_LENGTH)
    data["ema_previous"] = data["ema"].shift(1)

    for date in sorted({i.date() for i in data.index.tolist()}):
        tested_data = data.loc[data.index.date == date][["Close", "ema", "ema_previous"]]  # type: ignore
        lookback_data = get_lookback_data(data, date, settings.LOOKBACK_DAYS)

        if lookback_data.empty:
            continue

        backtest_one_day(tested_data, lookback_data, settings)
