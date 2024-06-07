import pandas as pd
from avanza.constants import Resolution, TimePeriod

from avanza_bank.client import Avanza
from utils.logger import get_logger

log = get_logger("avanza_bank.operators.chart")


class Chart:
    def __init__(self, client: Avanza):
        self.ctx = client

    def get_chart_data(self, instrument_id: str, period: TimePeriod, resolution: Resolution) -> pd.DataFrame:
        chart_data = self.ctx.get_chart_data(instrument_id, period, resolution)

        if not chart_data:
            log.warning(f"No chart data found for {instrument_id}")
            return pd.DataFrame(columns=["Datetime", "Open", "High", "Low", "Close", "Volume"]).set_index("Datetime")

        ohlc_data = [i.model_dump() for i in chart_data.ohlc]

        return pd.DataFrame(ohlc_data).set_index("Datetime")
