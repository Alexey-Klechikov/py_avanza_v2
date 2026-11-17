from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

from config import SETTINGS


@dataclass(frozen=True)
class DataWindow:
    """A half-open time range [start, end) of cached bars."""

    start: datetime
    end: datetime

    @classmethod
    def days_before(cls, end: datetime, days: int) -> "DataWindow":
        return cls(start=end - timedelta(days=days), end=end)

    def slice(self, data: pd.DataFrame) -> pd.DataFrame:
        """A copy of the bars in this window (callers add indicator columns to it)."""
        window_data = data.loc[(data.index >= self.start) & (data.index < self.end)].copy()
        window_data.index = pd.to_datetime(window_data.index)

        return window_data

    def __str__(self) -> str:
        return f"{self.start.date()} - {self.end.date()}"


@dataclass(frozen=True)
class CalibrationWindows:
    """Training ends where the holdout starts, so the final test only sees bars that training never saw."""

    training: DataWindow
    holdout: DataWindow

    @classmethod
    def ending(cls, end: datetime) -> "CalibrationWindows":
        holdout = DataWindow.days_before(end, SETTINGS.STRATEGY.HOLDOUT_DAYS)

        return cls(training=DataWindow.days_before(holdout.start, SETTINGS.STRATEGY.TRAIN_DAYS), holdout=holdout)
