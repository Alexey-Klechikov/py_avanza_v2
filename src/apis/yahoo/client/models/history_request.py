from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class Scale(Enum):
    MINUTE = "MINUTE"
    HOUR = "HOUR"
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
    YEAR = "YEAR"


class ScaledValue(BaseModel):
    raw: str
    num: int
    scale: Scale


class Period(Enum):
    ONE_DAY = ScaledValue(raw="1d", num=1, scale=Scale.DAY)
    FIVE_DAYS = ScaledValue(raw="5d", num=5, scale=Scale.DAY)
    ONE_MONTH = ScaledValue(raw="1mo", num=1, scale=Scale.MONTH)
    THREE_MONTHS = ScaledValue(raw="3mo", num=3, scale=Scale.MONTH)
    SIX_MONTHS = ScaledValue(raw="6mo", num=6, scale=Scale.MONTH)
    ONE_YEAR = ScaledValue(raw="1y", num=1, scale=Scale.YEAR)
    TWO_YEARS = ScaledValue(raw="2y", num=2, scale=Scale.YEAR)
    FIVE_YEARS = ScaledValue(raw="5y", num=5, scale=Scale.YEAR)
    TEN_YEARS = ScaledValue(raw="10y", num=10, scale=Scale.YEAR)

    def __str__(self):
        return self.value.raw

    @property
    def days(self) -> int:
        days_per_unit = DAYS_PER_SCALE_UNIT.get(self.value.scale)
        if days_per_unit is None:
            raise ValueError(f"Unknown scale: {self.value.scale}")

        return self.value.num * days_per_unit


class Interval(Enum):
    ONE_MINUTE = ScaledValue(raw="1m", num=1, scale=Scale.MINUTE)
    TWO_MINUTES = ScaledValue(raw="2m", num=2, scale=Scale.MINUTE)
    FIVE_MINUTES = ScaledValue(raw="5m", num=5, scale=Scale.MINUTE)
    FIFTEEN_MINUTES = ScaledValue(raw="15m", num=15, scale=Scale.MINUTE)
    THIRTY_MINUTES = ScaledValue(raw="30m", num=30, scale=Scale.MINUTE)
    SIXTY_MINUTES = ScaledValue(raw="60m", num=60, scale=Scale.MINUTE)
    NINETY_MINUTES = ScaledValue(raw="90m", num=90, scale=Scale.MINUTE)
    ONE_HOUR = ScaledValue(raw="1h", num=1, scale=Scale.HOUR)
    ONE_DAY = ScaledValue(raw="1d", num=1, scale=Scale.DAY)
    FIVE_DAYS = ScaledValue(raw="5d", num=5, scale=Scale.DAY)
    ONE_WEEK = ScaledValue(raw="1wk", num=1, scale=Scale.WEEK)
    ONE_MONTH = ScaledValue(raw="1mo", num=1, scale=Scale.MONTH)
    THREE_MONTHS = ScaledValue(raw="3mo", num=3, scale=Scale.MONTH)

    def __str__(self):
        return self.value.raw

    @property
    def mins(self) -> int:
        minutes_per_unit = MINUTES_PER_SCALE_UNIT.get(self.value.scale)
        if minutes_per_unit is None:
            raise ValueError(f"Unknown scale: {self.value.scale}")

        return self.value.num * minutes_per_unit


class HistoryRequest(BaseModel):
    period: Period | None = Field(default=None)
    interval: Interval = Interval.ONE_MINUTE
    start: date | None = Field(default=None)
    end: date | None = Field(default=None)

    def model_dump(self, **kwargs):
        request = {key: str(value) for key, value in super().model_dump(exclude_none=True, **kwargs).items()}

        if "period" in request and ("start" in request or "end" in request):
            raise ValueError("Either ['period'] or ['start' and 'end'] should be provided, not both.")

        return request


# Calendar approximations; `Interval.mins` deliberately has no WEEK or YEAR unit.
DAYS_PER_SCALE_UNIT = {Scale.DAY: 1, Scale.WEEK: 7, Scale.MONTH: 30, Scale.YEAR: 365}
MINUTES_PER_SCALE_UNIT = {
    Scale.MINUTE: 1,
    Scale.HOUR: 60,
    Scale.DAY: 60 * 24,
    Scale.WEEK: 60 * 24 * 7,
    Scale.MONTH: 60 * 24 * 30,
}
