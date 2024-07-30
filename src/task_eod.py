import platform
import warnings
from datetime import datetime, timedelta

from avanza.constants import Resolution, TimePeriod

from apis.avanza.operators import Chart
from apis.investing.client.models import Resolution as InvestingResolution
from apis.investing.operators.ticker import Ticker as InvestingTicker
from apis.telegram.operators import Telegram
from apis.yahoo.client.models import Interval, Period
from apis.yahoo.operators import Ticker as YahooTicker
from data.settings import OMX30_AVA, OMX30_INVESTING, OMX30_YAHOO
from operators import (
    backtest,
    get_exchange_working_hours,
    get_stock_events,
    update_exchange_working_hours,
    update_stock_events,
)
from services.storage import Storage
from services.ta.strategies.models import ComposeStrategiesListMethod
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)

set_handlers("eod")
log = get_logger()


def cache_omx30():
    log.warning("TASK 1: Cache OMX30 data")

    for resolution_ava, resolution_investing, interval_yahoo in [
        (Resolution.MINUTE, InvestingResolution.ONE_MINUTE, Interval.ONE_MINUTE),
        (Resolution.TWO_MINUTES, None, Interval.TWO_MINUTES),
        (Resolution.FIVE_MINUTES, InvestingResolution.FIVE_MINUTES, Interval.FIVE_MINUTES),
        (Resolution.HOUR, InvestingResolution.SIXTY_MINUTES, Interval.SIXTY_MINUTES),
    ]:
        storage = Storage(OMX30_YAHOO, resolution=interval_yahoo.value.raw)
        rows_before = storage.read().shape[0]

        data_ava = Chart.get_chart_data(OMX30_AVA, TimePeriod.TODAY, resolution_ava)
        storage.write(data_ava)

        if resolution_investing and platform.system() == "Darwin":  # TODO: fix investing API for Ubuntu
            data_investing = InvestingTicker(OMX30_INVESTING).get_history(resolution=resolution_investing, period_days=60)
            storage.write(data_investing)

        if storage.read().shape[0] == rows_before:
            data_yahoo = YahooTicker(OMX30_YAHOO).get_history(period=Period.FIVE_DAYS, interval=interval_yahoo)
            storage.write(data_yahoo)

        rows_after = storage.read().shape[0]
        log.info(f"Cached ({interval_yahoo.value.raw}): {rows_before} rows before -> {rows_after} rows after")


def backtest_strategies():
    resolution = "5m"
    period_days = 30

    log.warning(f"TASK 2: Backtest strategies on OMX30 | {resolution} | {period_days} days")

    data = Storage(OMX30_YAHOO, resolution=resolution).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    backtest(
        data,
        [],
        ComposeStrategiesListMethod.READ,
        old_strategies_file_name="strategies_dev_6_indicators.json",
        new_strategies_file_name="strategies.json",
        plot=False,
    )


def gather_analytics():
    log.warning("TASK 3: Gather analytics")

    update_exchange_working_hours(shift_days=1)
    exchange_working_hours = get_exchange_working_hours(shift_days=1)
    if not exchange_working_hours:
        log.info("No upcoming events")
    else:
        for daytime, events in exchange_working_hours.items():
            if any(
                [
                    datetime.strptime(daytime, "%H:%M:%S") <= datetime.strptime("09:00", "%H:%M"),
                    datetime.strptime(daytime, "%H:%M:%S") >= datetime.strptime("17:30", "%H:%M"),
                ],
            ):
                continue

            log.info(f"{daytime}: {', '.join(events)}")

    update_stock_events()
    stock_events = get_stock_events(shift_days=1)
    if not stock_events:
        log.info("No upcoming events")
    else:
        for event in stock_events:
            log.info(event)


if __name__ == "__main__":
    try:
        cache_omx30()
        backtest_strategies()
        gather_analytics()

    except Exception as e:
        telegram = Telegram()
        telegram.messages = ["Error in task_eod.py"]
        telegram.send_message()

        raise e
