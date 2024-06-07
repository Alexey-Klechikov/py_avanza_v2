from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, field_validator


class OHLC(BaseModel):
    Datetime: datetime = Field(alias="timestamp")
    Open: float = Field(alias="open")
    High: float = Field(alias="high")
    Low: float = Field(alias="low")
    Close: float = Field(alias="close")
    Volume: int = Field(alias="totalVolumeTraded")

    @field_validator("Datetime", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        if v is None:
            return None

        return datetime.fromtimestamp(v / 1000)


class Resolution(BaseModel):
    chart_resolution: str = Field(alias="chartResolution")
    available_resolutions: List[str] = Field(alias="availableResolutions")


class Metadata(BaseModel):
    resolution: Resolution


class ChartData(BaseModel):
    ohlc: List[OHLC]
    metadata: Metadata
    previous_closing_price: float = Field(alias="previousClosingPrice")
