import warnings
from datetime import datetime, timedelta

from avanza.constants import Resolution, TimePeriod

from apis.avanza.operators import Chart
from apis.telegram.operators import Telegram
from apis.yahoo.client.models import Interval, Period
from apis.yahoo.operators import Ticker
from data.settings import OMX30_AVA, OMX30_YAHOO
from operators import backtest, get_stock_events, update_stock_events
from services.storage import Storage
from services.ta.strategies.models import ComposeStrategiesListMethod
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)

set_handlers("eod")
log = get_logger()


def cache_omx30():
    log.warning("TASK 1: Cache OMX30 data")

    for period_ava, resolution_ava, period_yahoo, interval_yahoo in [
        (TimePeriod.TODAY, Resolution.MINUTE, Period.FIVE_DAYS, Interval.ONE_MINUTE),
        (TimePeriod.TODAY, Resolution.TWO_MINUTES, Period.ONE_MONTH, Interval.TWO_MINUTES),
        (TimePeriod.TODAY, Resolution.FIVE_MINUTES, Period.ONE_MONTH, Interval.FIVE_MINUTES),
        (TimePeriod.ONE_WEEK, Resolution.HOUR, Period.ONE_MONTH, Interval.SIXTY_MINUTES),
    ]:
        storage = Storage(OMX30_YAHOO, resolution=interval_yahoo.value.raw)
        rows_before = storage.read().shape[0]

        data_ava = Chart.get_chart_data(OMX30_AVA, period_ava, resolution_ava)
        storage.write(data_ava)

        data_yahoo = Ticker(OMX30_YAHOO).get_history(period=period_yahoo, interval=interval_yahoo)
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
        old_strategies_file_name="dev_strategies_5_indicators.json",
        new_strategies_file_name="strategies.json",
        plot=False,
    )


def gather_analytics():
    log.warning("TASK 3: Gather analytics")

    update_stock_events()
    stock_events = get_stock_events(shift_days=1)
    if not stock_events:
        log.info("No upcoming events")
        return

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
