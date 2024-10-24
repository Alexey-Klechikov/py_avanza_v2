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
        if self.value.scale == Scale.DAY:
            return self.value.num

        elif self.value.scale == Scale.WEEK:
            return self.value.num * 7

        elif self.value.scale == Scale.MONTH:
            return self.value.num * 30

        elif self.value.scale == Scale.YEAR:
            return self.value.num * 365

        else:
            raise ValueError(f"Unknown scale: {self.value.scale}")


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
        if self.value.scale == Scale.MINUTE:
            return self.value.num

        elif self.value.scale == Scale.HOUR:
            return self.value.num * 60

        elif self.value.scale == Scale.DAY:
            return self.value.num * 60 * 24

        elif self.value.scale == Scale.MONTH:
            return self.value.num * 60 * 24 * 30

        else:
            raise ValueError(f"Unknown scale: {self.value.scale}")


class HistoryRequest(BaseModel):
    period: Period | None = Field(default=None)  # Either Use period parameter or use start and end
    interval: Interval = Interval.ONE_MINUTE  # Default is 1 minute
    start: date | None = Field(default=None)  # Default is 99 years ago
    end: date | None = Field(default=None)  # Default is now
    prepost: bool | None = Field(default=None)  # Include Pre and Post market data in results
    auto_adjust: bool | None = Field(default=None)  # Adjust all OHLC automatically? Default is True
    back_adjust: bool | None = Field(default=None)  # Back-adjusted data to mimic true historical prices
    repair: bool | None = Field(default=None)  # Detect currency unit 100x mixups and attempt repair.
    keepna: bool | None = Field(default=None)  # Keep NaN rows returned by Yahoo
    proxy: str | None = Field(default=None)  # Optional. Proxy server URL scheme. Default is None
    rounding: bool | None = Field(default=None)  # Round values to 2 decimal places
    timeout: float | None = Field(
        default=None,
    )  # If not None stops waiting for a response after given number of seconds
    raise_errors: bool | None = Field(default=None)  # If True, then raise errors as Exceptions instead of logging

    def model_dump(self, **kwargs):
        request = super().model_dump(exclude_none=True, **kwargs)
        request = {k: str(v) for k, v in request.items()}

        if "period" in request and ("start" in request or "end" in request):
            raise ValueError("Either ['period'] or ['start' and 'end'] should be provided, not both.")

        return request
