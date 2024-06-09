import pandas as pd
import yfinance as yf

from services.yahoo.client.models import HistoryRequest
from utils.logger import get_logger

log = get_logger()


class Yahoo:
    def __init__(self):
        pass

    @classmethod
    def get_history(self, ticker_yahoo: str, **kwargs) -> pd.DataFrame:
        ticker = yf.Ticker(ticker_yahoo)
        return ticker.history(**HistoryRequest(**kwargs).model_dump())
