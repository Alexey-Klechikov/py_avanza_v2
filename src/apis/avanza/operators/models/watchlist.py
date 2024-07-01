from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class Orderbook(BaseModel):
    id: str
    type: str
    name: str
    spread: Optional[float]
    buy: Optional[float]
    sell: Optional[float]
    leverage: float
    start_date: date


class ValidInstruments(BaseModel):
    BULL: List[Orderbook] = Field(default_factory=list)
    BEAR: List[Orderbook] = Field(default_factory=list)


class PreferredInstrument(BaseModel):
    BULL: Optional[Orderbook] = Field(default=None)
    BEAR: Optional[Orderbook] = Field(default=None)
