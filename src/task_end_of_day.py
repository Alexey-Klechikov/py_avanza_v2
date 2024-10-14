import platform
import warnings
from datetime import datetime, timedelta

import pandas as pd
from avanza.constants import Resolution, TimePeriod

from apis.avanza.operators import Chart
from apis.investing.client.models import Resolution as InvestingResolution
from apis.investing.operators import Ticker as InvestingTicker
from apis.telegram.operators import Telegram
from apis.yahoo.client.models import Interval, Period
from apis.yahoo.operators import Ticker as YahooTicker
from backtest import backtest_hold_interday, backtest_hold_intraday
from backtest import backtest_strategies as _backtest_strategies
from config import SETTINGS_HOLD_OMX_DT, SETTINGS_TRADE_OMX
from services.hold.models import Direction, Scope
from services.hold.operators import Backlog
from services.storage import Storage
from services.ta.strategies.models import ComposeStrategiesListMethod
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)

set_handlers("end_of_day")
log = get_logger()


def cache_history(settings):
    log.warning(f"TASK: Cache {settings.NAME} data")

    for resolution_ava, resolution_investing, interval_yahoo in [
        (Resolution.MINUTE, InvestingResolution.ONE_MINUTE, Interval.ONE_MINUTE),
        (Resolution.TWO_MINUTES, None, Interval.TWO_MINUTES),
        (Resolution.FIVE_MINUTES, InvestingResolution.FIVE_MINUTES, Interval.FIVE_MINUTES),
        (Resolution.HOUR, InvestingResolution.SIXTY_MINUTES, Interval.SIXTY_MINUTES),
    ]:
        storage = Storage(settings, resolution=interval_yahoo.value.raw)
        rows_before = storage.read().shape[0]

        if settings.TRADING_DATA == "avanza":
            data_ava = Chart.get_chart_data(settings, TimePeriod.TODAY, resolution_ava)
            storage.write(data_ava)

        elif settings.TRADING_DATA == "yahoo":
            data_yahoo = YahooTicker(settings).get_history(period=Period.FIVE_DAYS, interval=interval_yahoo)
            storage.write(data_yahoo)

        if False and resolution_investing and platform.system() == "Darwin":
            for i in range(5, 60, 5):
                data_investing = InvestingTicker(settings).get_history(
                    resolution=resolution_investing,
                    period_days=i,
                )
                storage.write(data_investing)

        rows_after = storage.read().shape[0]
        log.info(f"Cached ({interval_yahoo.value.raw}): {rows_before} rows before -> {rows_after} rows after")


def backtest_strategies(settings, period_days: int):
    log.warning(f"TASK: Backtest strategies on {settings.NAME} | {settings.RESOLUTION} | {period_days} days")

    data = Storage(settings).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    _backtest_strategies(
        data,
        ComposeStrategiesListMethod.READ,
        settings,
        old_strategies_file_name=f"strategies_dev_{settings.TRADING_STRATEGY_INDICATORS}.json",
        new_strategies_file_name="strategies.json",
        plot=False,
    )


def generate_hold_rules_intraday(settings, period_days: int, slice_duration: int) -> None:
    log.warning(
        f"Generating INTRADAY hold rules using period {period_days} days "
        + f"using slice_duration {slice_duration} mins.",
    )

    times = [i.time() for i in pd.date_range(start="09:58", end="16:58", freq=f"{slice_duration}min")]
    buy_time_sell_time_combinations = [
        (buy_time, sell_time) for buy_time in times for sell_time in times if buy_time < sell_time
    ]

    data = Storage(settings).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]
    data.index = pd.to_datetime(data.index)

    backlog = Backlog()
    for direction in [Direction.BULL, Direction.BEAR]:
        hold_rules_per_direction = backtest_hold_intraday(
            data,
            buy_time_sell_time_combinations,
            direction,
            settings.REF_PRICE,
        )

        backlog.rules += hold_rules_per_direction

    for hold_rule in backlog.rules:
        log.info(f"Hold Rule: {hold_rule.dump_dict()}")

    backlog.write_rules(settings, Scope.INTRADAY)


def generate_hold_rules_interday(settings, period_days: int, slice_duration: int) -> None:
    direction = Direction.BULL

    log.warning(
        f"Generating INTERDAY hold rules using period {period_days} days "
        + f"for direction {direction.value} using slice_duration {slice_duration} mins.",
    )

    eod_times = [i.time() for i in pd.date_range(start="16:50", end="17:16", freq=f"{slice_duration}min")]
    close_times = [i.time() for i in pd.date_range(start="09:02", end="09:58", freq=f"{slice_duration}min")]

    data = Storage(settings).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    hold_rule = backtest_hold_interday(data, eod_times, close_times, direction, settings.REF_PRICE)

    log.info(f"Hold Rule: {hold_rule.dump_dict()}")

    backlog = Backlog()
    backlog.rules.append(hold_rule)
    backlog.write_rules(settings, Scope.INTERDAY)


if __name__ == "__main__":
    try:
        cache_history(SETTINGS_TRADE_OMX)
        backtest_strategies(SETTINGS_TRADE_OMX, period_days=40)
        generate_hold_rules_intraday(SETTINGS_HOLD_OMX_DT, period_days=40, slice_duration=4)
        generate_hold_rules_interday(SETTINGS_HOLD_OMX_DT, period_days=40, slice_duration=2)

    except Exception as e:
        telegram = Telegram()
        telegram.messages = ["Error in task_eod.py"]
        telegram.send_message()

        raise e
