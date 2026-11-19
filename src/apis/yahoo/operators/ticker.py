from datetime import date, timedelta

import pandas as pd

from apis.yahoo.client.client import Yahoo
from apis.yahoo.client.models.history_request import Interval, Period
from utils.logger.operators import get_logger

log = get_logger()

AVAILABLE_PERIOD_DAYS_BY_INTERVAL_MINUTES = {1: 22, 2: 42, 5: 55}
CHUNK_DAYS = 5


class Ticker:
    def _get_extended_history(self, period: Period, interval: Interval) -> pd.DataFrame:
        available_period_days = AVAILABLE_PERIOD_DAYS_BY_INTERVAL_MINUTES.get(interval.mins, period.days)
        if period.days > available_period_days:
            log.debug(
                f"Period {period.days} days is not available for interval {interval.mins} minutes. "
                f"Using {available_period_days} days instead.",
            )

        dates = pd.date_range(
            start=date.today() - timedelta(days=min(period.days, available_period_days)),
            end=date.today() + timedelta(days=1),
        )

        history_chunks = [pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])]
        for chunk_start_index in range(0, len(dates), CHUNK_DAYS):
            chunk_start = dates[chunk_start_index]
            chunk_end = min(chunk_start + timedelta(days=CHUNK_DAYS), dates[-1])
            history_chunks.append(Yahoo.get_history(interval=interval, start=chunk_start, end=chunk_end))

        history = pd.concat(history_chunks)
        return history[~history.index.duplicated(keep="last")].sort_index()

    def get_history(self, period: Period, interval: Interval) -> pd.DataFrame:
        log.debug(f"Fetch chart data [{period} - {interval}]")

        history = (
            self._get_extended_history(period, interval)
            if period.days > 7 and interval.mins <= 5
            else Yahoo.get_history(period=period, interval=interval)
        )

        history.index = (
            history.index.rename("Datetime").tz_convert("Europe/Stockholm").tz_localize(None)  # type: ignore
        )

        return history
