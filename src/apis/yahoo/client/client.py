import pandas as pd
import yfinance as yf

from apis.yahoo.client.models import HistoryRequest
from config import SETTINGS
from utils.logger import get_logger

log = get_logger()


class Yahoo:
    @staticmethod
    def get_history(**kwargs) -> pd.DataFrame:
        ticker = yf.Ticker(SETTINGS.YAHOO)
        return ticker.history(**HistoryRequest(**kwargs).model_dump())
