from typing import Optional

from avanza.constants import InstrumentType
from pydantic import BaseModel


class Instrument(BaseModel):
    id: str
    type: InstrumentType
    name: str


class Quote(BaseModel):
    buy: Optional[float]
    sell: Optional[float]


class Performance(BaseModel):
    percent: float
    value: float


class Position(BaseModel):
    instrument: Instrument
    quote: Quote
    volume: float
    value: float

    acquired_price: float
    acquired_value: float

    performance: Performance
