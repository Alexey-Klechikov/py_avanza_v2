import warnings
from datetime import timedelta

import pandas as pd
from avanza.constants import Resolution, TimePeriod

from apis.avanza.operators.chart import Chart
from apis.telegram.operators import Telegram
from apis.yahoo.client.models.history_request import Interval, Period
from apis.yahoo.operators.ticker import Ticker as YahooTicker
from config import SETTINGS
from services.storage.operators import Storage
from services.ta.strategies.models.strategy import ComposeStrategiesListMethod
from tasks.trade_strategies.backtest import backtest_trade_strategies as _backtest_trade_strategies
from utils.constants import TODAY_MIDNIGHT
from utils.logger.operators import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)

set_handlers("end_of_day")
log = get_logger()


def _get_data(period_days: int):
    data = Storage().read()
    data = data.loc[(data.index >= TODAY_MIDNIGHT - timedelta(days=period_days)) & (data.index < TODAY_MIDNIGHT)]
    data.index = pd.to_datetime(data.index)

    return data


def cache_history():
    log.warning(f"TASK: Cache {SETTINGS.NAME} data")

    for resolution_ava, interval_yahoo in [
        (Resolution.MINUTE, Interval.ONE_MINUTE),
        (Resolution.TWO_MINUTES, Interval.TWO_MINUTES),
        (Resolution.FIVE_MINUTES, Interval.FIVE_MINUTES),
        (Resolution.HOUR, Interval.SIXTY_MINUTES),
        (Resolution.DAY, Interval.ONE_DAY),
    ]:
        storage = Storage(resolution=interval_yahoo.value.raw)
        rows_before = storage.read().shape[0]

        if SETTINGS.DATA_SOURCE == "yahoo":
            try:
                data_yahoo = YahooTicker().get_history(period=Period.FIVE_DAYS, interval=interval_yahoo)
                storage.write(data_yahoo)
            except Exception as e:
                log.error(f"Error fetching Yahoo data: {e}")
                SETTINGS.DATA_SOURCE = "avanza"

        if SETTINGS.DATA_SOURCE == "avanza":
            data_ava = Chart.get_chart_data(TimePeriod.TODAY, resolution_ava)
            storage.write(data_ava)

        rows_after = storage.read().shape[0]
        log.info(f"Cached ({interval_yahoo.value.raw}): {rows_before} rows before -> {rows_after} rows after")


def backtest_trade_strategies(period_days: int):
    log.warning(f"TASK: Backtest strategies on {SETTINGS.NAME} | {SETTINGS.RESOLUTION} | {period_days} days")

    _backtest_trade_strategies(
        _get_data(period_days),
        ComposeStrategiesListMethod.READ,
        strategies_file_name_suffix_old=f"dev_{SETTINGS.STRATEGY.INDICATORS}",
    )


if __name__ == "__main__":
    try:
        cache_history()
        backtest_trade_strategies(period_days=30)

    except Exception as e:
        telegram = Telegram()
        telegram.messages = ["Error in task_eod.py"]
        telegram.send_message()

        raise e
