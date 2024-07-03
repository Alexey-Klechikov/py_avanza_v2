import warnings

from avanza.constants import Resolution, TimePeriod

from apis.avanza.operators import Chart
from apis.yahoo.client.models import Interval, Period
from apis.yahoo.operators import Ticker
from data.settings import OMX30_AVA, OMX30_YAHOO
from services.storage import Storage
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.simplefilter(action="ignore", category=UserWarning)

set_handlers("eod")
log = get_logger()


def cache_omx30():
    for period_ava, resolution_ava, period_yahoo, interval_yahoo in [
        (TimePeriod.TODAY, Resolution.MINUTE, Period.ONE_MONTH, Interval.ONE_MINUTE),
        (TimePeriod.TODAY, Resolution.TWO_MINUTES, Period.THREE_MONTHS, Interval.TWO_MINUTES),
        (TimePeriod.TODAY, Resolution.FIVE_MINUTES, Period.THREE_MONTHS, Interval.FIVE_MINUTES),
        (TimePeriod.ONE_WEEK, Resolution.HOUR, Period.ONE_YEAR, Interval.SIXTY_MINUTES),
        (TimePeriod.ONE_YEAR, Resolution.DAY, Period.ONE_YEAR, Interval.ONE_DAY),
    ]:
        storage = Storage(OMX30_YAHOO, resolution=interval_yahoo.value.raw)
        rows_before = storage.read().shape[0]

        data_ava = Chart.get_chart_data(OMX30_AVA, period_ava, resolution_ava)
        storage.write(data_ava)

        data_yahoo = Ticker(OMX30_YAHOO).get_history(period=period_yahoo, interval=interval_yahoo)
        storage.write(data_yahoo)

        rows_after = storage.read().shape[0]
        log.info(f"Cached ({interval_yahoo.value.raw}): {rows_before} rows before -> {rows_after} rows after")


if __name__ == "__main__":
    cache_omx30()
