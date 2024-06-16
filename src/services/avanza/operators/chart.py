import pandas as pd
from avanza.constants import Resolution, TimePeriod

from services.avanza.client import get_client
from utils.logger import get_logger

log = get_logger()


class Chart:
    def __init__(self):
        pass

    @classmethod
    def get_chart_data(cls, instrument_id: str, period: TimePeriod, resolution: Resolution) -> pd.DataFrame:
        log.debug(f"Fetching chart data for {instrument_id} with period {period} and resolution {resolution}")

        chart_data = get_client().get_chart_data(instrument_id, period, resolution)

        if not chart_data:
            log.warning(f"No chart data found for {instrument_id}")
            return pd.DataFrame(columns=["Datetime", "Open", "High", "Low", "Close", "Volume"]).set_index("Datetime")

        ohlc_data = [i.model_dump() for i in chart_data.ohlc]

        return pd.DataFrame(ohlc_data).set_index("Datetime")
