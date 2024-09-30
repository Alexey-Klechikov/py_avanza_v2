import platform
import warnings
from datetime import datetime, timedelta

from avanza.constants import Resolution, TimePeriod

from apis.avanza.operators import Chart
from apis.investing.client.models import Resolution as InvestingResolution
from apis.investing.operators import Ticker as InvestingTicker
from apis.telegram.operators import Telegram
from apis.yahoo.client.models import Interval, Period
from apis.yahoo.operators import Ticker as YahooTicker
from backtest import backtest_strategies as _backtest_strategies
from config import SETTINGS_TRADE_OMX
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

        if settings.TRADING_DATA == "ava":
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


def backtest_strategies(settings):
    period_days = 60

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


if __name__ == "__main__":
    try:
        cache_history(SETTINGS_TRADE_OMX)
        backtest_strategies(SETTINGS_TRADE_OMX)

    except Exception as e:
        telegram = Telegram()
        telegram.messages = ["Error in task_eod.py"]
        telegram.send_message()

        raise e
