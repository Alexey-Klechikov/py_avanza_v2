import warnings
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import pandas as pd
from avanza.constants import Resolution, TimePeriod

from apis.avanza.operators import Chart
from apis.avanza.trade.models import Direction
from hold_correlation import BacklogHoldCorrelation
from hold_correlation.models import Correlation, HoldRuleCorrelation, Interval
from services import Storage
from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

log = get_logger()


# def sleep_until_next_event(event: Event) -> None:
#     if event is None:
#         return

#     sleep_time = (datetime.combine(datetime.today(), event.at) - datetime.now()).seconds
#     hours, remainder = divmod(sleep_time, 3600)
#     minutes, remainder = divmod(remainder, 60)

#     if (datetime.now() - datetime.combine(datetime.today(), event.at)).seconds < 120:
#         return

#     log.info(f"Sleeping for {hours}:{minutes}:{remainder}")

#     sleep(sleep_time)

#     get_client.cache_clear()


class Data:
    def __init__(self, settings):
        self.settings = settings
        self.data: pd.DataFrame = pd.DataFrame()
        self.slice_duration = 10

    def get(self):
        storage = Storage(self.settings)
        storage.write(Chart.get_chart_data(self.settings, TimePeriod.TODAY, Resolution.FIVE_MINUTES))
        data = storage.read()

        self.data = data.loc[data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)]

        resampled_data = self.data.resample(f"{self.slice_duration}min")
        self.data = pd.DataFrame(
            {
                "Open": resampled_data["Open"].first(),
                "Close": resampled_data["Close"].last(),
                "High": resampled_data["Close"].max(),
                "Low": resampled_data["Close"].min(),
            },
        ).dropna()


@dataclass
class Action:
    multiplier: float
    price_difference: float
    efficiency: float
    direction: Direction


def get_interval_price_difference(
    interval: Interval,
    data: pd.DataFrame,
) -> float:
    tested_interval_rows = data.between_time(interval.start, interval.end)
    return tested_interval_rows["Close"].iloc[-2] - tested_interval_rows["Open"].iloc[0]


def get_deciding_rule(
    settings,
    hold_rules: List[HoldRuleCorrelation],
    data: Data,
) -> Optional[Action]:
    actions: List[Action] = []
    total_efficiency_coefficient = 0

    for hold_rule in hold_rules:
        price_difference = get_interval_price_difference(hold_rule.deciding_interval, data.data)
        if abs(price_difference) < settings.MIN_DECIDING_PRICE_CHANGE:
            continue

        direction_coefficient = (1 if hold_rule.correlation == Correlation.SAME else -1) * (
            1 if price_difference > 0 else -1
        )
        total_efficiency_coefficient += direction_coefficient * hold_rule.efficiency
        actions.append(
            Action(
                multiplier=hold_rule.multiplier,
                price_difference=abs(round(price_difference, 2)),
                efficiency=hold_rule.efficiency,
                direction=Direction("BULL" if direction_coefficient > 0 else "BEAR"),
            ),
        )

    action_direction = Direction("BULL" if total_efficiency_coefficient > 0 else "BEAR")

    actions = [i for i in actions if i.direction == action_direction]
    if not actions:
        return

    log.info(f"Total efficiency coefficient: {total_efficiency_coefficient} -> {action_direction}")

    return max(actions, key=lambda x: (x.efficiency, x.price_difference))


# MAIN
def hold(dry_run: bool, settings) -> None:
    log.info("Start holding" + (" | DRY_RUN" if dry_run else ""))

    data = Data(settings)
    data.get()

    backlog = BacklogHoldCorrelation()
    backlog.read_rules(settings)

    times = [i.time() for i in pd.date_range(start="10:00", end="17:00", freq="10min")]

    for i in times:
        hold_rules = backlog.get_rules(i)

        print("-----\nTESTED_TIME", i)

        if not hold_rules:
            continue

        action = get_deciding_rule(settings, hold_rules, data)
        print("ACTION", action)
