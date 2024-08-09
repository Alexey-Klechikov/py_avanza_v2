import pandas as pd
from avanza.constants import Resolution, TimePeriod

from apis.avanza.client import get_client
from utils.logger import get_logger

log = get_logger()


class Chart:
    def __init__(self):
        pass

    @classmethod
    def get_chart_data(cls, instrument_id: str, period: TimePeriod, resolution: Resolution) -> pd.DataFrame:
        log.debug(f"Fetch chart data [{period.name} - {resolution.name}]")

        available_period = period
        if resolution in [Resolution.MINUTE, Resolution.TWO_MINUTES, Resolution.FIVE_MINUTES]:
            available_period = TimePeriod.TODAY
        elif period != TimePeriod.TODAY and resolution in [Resolution.TEN_MINUTES, Resolution.THIRTY_MINUTES]:
            available_period = TimePeriod.ONE_WEEK
        elif period not in [TimePeriod.TODAY, TimePeriod.ONE_WEEK] and resolution == Resolution.HOUR:
            available_period = TimePeriod.ONE_MONTH

        if available_period and period != available_period:
            log.debug(
                f"Period {period.name} is not available for resolution {resolution.name}. "
                f"Using {available_period.name} instead.",
            )
            period = available_period

        chart_data = get_client().get_chart_data(instrument_id, period, resolution)

        if not chart_data:
            log.warning(f"No chart data found for {instrument_id}")
            return pd.DataFrame(columns=["Datetime", "Open", "High", "Low", "Close", "Volume"]).set_index("Datetime")

        ohlc_data = [i.model_dump() for i in chart_data.ohlc]

        return pd.DataFrame(ohlc_data).set_index("Datetime")
