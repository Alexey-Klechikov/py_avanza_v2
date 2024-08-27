from datetime import date, timedelta

import pandas as pd

from apis.yahoo.client import Yahoo
from apis.yahoo.client.models import Interval, Period
from utils.logger import get_logger

log = get_logger()


class Ticker:
    def __init__(self, settings):
        self.ticker_yahoo = settings.YAHOO

    def _get_extended_history(
        self,
        period: Period,
        interval: Interval,
    ) -> pd.DataFrame:
        history = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

        available_period_days = period.days
        if interval.mins == 1:
            available_period_days = 22
        elif interval.mins == 2:
            available_period_days = 42
        elif interval.mins == 5:
            available_period_days = 55

        if period.days > available_period_days:
            log.debug(
                f"Period {period.days} days is not available for interval {interval.mins} minutes. "
                f"Using {available_period_days} days instead.",
            )

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
                    Yahoo.get_history(
                        ticker_yahoo=self.ticker_yahoo,
                        interval=interval,
                        start=start_date,
                        end=end_date,
                    ),
                ],
            )

        return history.drop_duplicates().sort_index(axis=0)

    def get_history(self, period: Period, interval: Interval) -> pd.DataFrame:
        log.debug(f"Fetching history for {self.ticker_yahoo} with period {period} and interval {interval}")

        history = (
            self._get_extended_history(period, interval)
            if period.days > 7 and interval.mins <= 5
            else Yahoo.get_history(ticker_yahoo=self.ticker_yahoo, period=period, interval=interval)
        )

        history.index = history.index.rename("Datetime").tz_convert("Europe/Stockholm").tz_localize(None)

        return history
