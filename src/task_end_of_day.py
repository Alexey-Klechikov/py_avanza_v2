import warnings

from avanza.constants import Resolution, TimePeriod

from apis.avanza.operators.chart import Chart
from apis.telegram.operators import Telegram
from apis.yahoo.client.models.history_request import Interval, Period
from apis.yahoo.operators.ticker import Ticker as YahooTicker
from config import SETTINGS
from services.storage.operators import Storage
from tasks.backtest.paper_trade import paper_trade_session
from utils.constants import TODAY_MIDNIGHT
from utils.logger.operators import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)

set_handlers("end_of_day")
log = get_logger()


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
            data_yahoo = YahooTicker().get_history(period=Period.FIVE_DAYS, interval=interval_yahoo)
            storage.write(data_yahoo)

        elif SETTINGS.DATA_SOURCE == "avanza":
            data_ava = Chart.get_chart_data(TimePeriod.TODAY, resolution_ava)
            storage.write(data_ava)

        rows_after = storage.read().shape[0]
        log.info(f"Cached ({interval_yahoo.value.raw}): {rows_before} rows before -> {rows_after} rows after")


if __name__ == "__main__":
    try:
        cache_history()
        paper_trade_session(TODAY_MIDNIGHT.date())

    except Exception as e:
        telegram = Telegram()
        telegram.messages = ["Error in task_eod.py"]
        telegram.send_message()

        raise e
