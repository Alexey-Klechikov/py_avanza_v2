from datetime import datetime

from pydantic import BaseModel


class InstrumentInfo(BaseModel):
    received_time: datetime
    buy: float
    sell: float
    last: float
    highest: float
    lowest: float
    change: float
    change_percent: float
    spread: float
    spread_market_maker: float
    time_of_last: datetime
    total_value_traded: float
    total_volume_traded: int
    updated: datetime
