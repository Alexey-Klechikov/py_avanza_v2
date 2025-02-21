import warnings
from datetime import timedelta

import pandas as pd
from avanza.constants import Resolution, TimePeriod

from apis.avanza.operators import Chart
from apis.telegram.operators import Telegram
from apis.yahoo.client.models import Interval, Period
from apis.yahoo.operators import Ticker as YahooTicker
from config import SETTINGS_TRADE_STRATEGIES_GULD, SETTINGS_TRADE_STRATEGIES_OMX
from services import Storage
from services.ta.strategies.models import ComposeStrategiesListMethod
from tasks.trade_strategies import backtest_trade_strategies as _backtest_trade_strategies
from utils.constants import TODAY_MIDNIGHT
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)

set_handlers("end_of_day")
log = get_logger()


def _get_data(period_days: int, settings, resolution: str | None = None):
    data = Storage(settings, resolution).read()
    data = data.loc[(data.index >= TODAY_MIDNIGHT - timedelta(days=period_days)) & (data.index < TODAY_MIDNIGHT)]
    data.index = pd.to_datetime(data.index)

    return data


def cache_history(settings):
    log.warning(f"TASK: Cache {settings.NAME} data")

    for resolution_ava, interval_yahoo in [
        (Resolution.MINUTE, Interval.ONE_MINUTE),
        (Resolution.TWO_MINUTES, Interval.TWO_MINUTES),
        (Resolution.FIVE_MINUTES, Interval.FIVE_MINUTES),
        (Resolution.HOUR, Interval.SIXTY_MINUTES),
    ]:
        storage = Storage(settings, resolution=interval_yahoo.value.raw)
        rows_before = storage.read().shape[0]

        if settings.TRADING_DATA == "yahoo":
            try:
                data_yahoo = YahooTicker(settings).get_history(period=Period.FIVE_DAYS, interval=interval_yahoo)
                storage.write(data_yahoo)
            except Exception as e:
                log.error(f"Error fetching Yahoo data: {e}")
                settings.TRADING_DATA = "avanza"

        if settings.TRADING_DATA == "avanza":
            data_ava = Chart.get_chart_data(settings, TimePeriod.TODAY, resolution_ava)
            storage.write(data_ava)

        rows_after = storage.read().shape[0]
        log.info(f"Cached ({interval_yahoo.value.raw}): {rows_before} rows before -> {rows_after} rows after")


def backtest_trade_strategies(settings, period_days: int):
    log.warning(f"TASK: Backtest strategies on {settings.NAME} | {settings.RESOLUTION} | {period_days} days")

    _backtest_trade_strategies(
        _get_data(period_days, settings),
        ComposeStrategiesListMethod.READ,
        settings,
        strategies_file_name_suffix_old=f"dev_{settings.TRADING_STRATEGY_INDICATORS}",
    )


if __name__ == "__main__":
    try:
        cache_history(SETTINGS_TRADE_STRATEGIES_GULD)
        cache_history(SETTINGS_TRADE_STRATEGIES_OMX)
        backtest_trade_strategies(SETTINGS_TRADE_STRATEGIES_GULD, period_days=40)
        backtest_trade_strategies(SETTINGS_TRADE_STRATEGIES_OMX, period_days=40)

    except Exception as e:
        telegram = Telegram()
        telegram.messages = ["Error in task_eod.py"]
        telegram.send_message()

        raise e
