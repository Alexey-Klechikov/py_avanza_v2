from datetime import datetime, timedelta
from typing import Union

import pandas as pd

from apis.investing.client import get_investing
from apis.investing.client.models import Resolution
from data.settings import NASDAQ, OMX
from utils.logger import get_logger

log = get_logger()


class Ticker:
    def __init__(self, settings_index: Union[OMX, NASDAQ]):
        self.ticker_investing = settings_index.INVESTING

    def get_history(self, resolution: Resolution, period_days: int) -> pd.DataFrame:
        log.debug(
            f"Fetching history for {self.ticker_investing} "
            + f"with period {period_days} days and resolution {resolution.value} min",
        )

        history = get_investing(self.ticker_investing).get_history(
            resolution=resolution,
            from_datetime=datetime.now() - timedelta(days=period_days),
            to_datetime=datetime.now(),
        )
        history.index = pd.to_datetime(history.index) + timedelta(hours=2)

        return history
