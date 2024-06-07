from pydantic import BaseModel, Field, field_validator
from typing import List
from datetime import datetime


class OHLC(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    total_volume_traded: int = Field(alias="totalVolumeTraded")

    @field_validator("timestamp", mode="before")
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
