from datetime import date, timedelta

import pandas as pd

from services.yahoo.client import Yahoo
from services.yahoo.client.models import Interval, Period
from utils.logger import get_logger

log = get_logger()


class Ticker:
    def __init__(self):
        pass

    @classmethod
    def _get_extended_history(
        cls,
        ticker_yahoo: str,
        period: Period,
        interval: Interval,
    ) -> pd.DataFrame:
        history = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

        # 1m data is available for max 30 days
        # 2m & 5m data is available for max 60 days
        available_period_days = 29 if interval.mins == 1 else 59

        dates = pd.date_range(
            start=date.today() - timedelta(days=min(period.days, available_period_days)),
            end=date.today() + timedelta(days=1),
        )

        for i in range(0, len(dates), 5):
            start_date = dates[i]
            end_date = min(start_date + timedelta(days=5), dates[-1])

            history = pd.concat(
                [
                    history,
                    Yahoo.get_history(ticker_yahoo=ticker_yahoo, interval=interval, start=start_date, end=end_date),
                ],
            )

        return history.drop_duplicates().sort_index(axis=0)

    @classmethod
    def get_history(cls, ticker_yahoo: str, period: Period, interval: Interval) -> pd.DataFrame:
        log.info(f"Fetching history for {ticker_yahoo} with period {period} and interval {interval}")

        return (
            cls._get_extended_history(ticker_yahoo, period, interval)
            if period.days > 7 and interval.mins <= 5
            else Yahoo.get_history(ticker_yahoo=ticker_yahoo, period=period, interval=interval)
        )
