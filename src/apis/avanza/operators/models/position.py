from avanza.constants import InstrumentType
from pydantic import BaseModel


class Instrument(BaseModel):
    id: str
    type: InstrumentType
    name: str


class Quote(BaseModel):
    buy: float | None
    sell: float | None


class Performance(BaseModel):
    percent: float | None
    value: float | None


class Position(BaseModel):
    instrument: Instrument
    quote: Quote
    volume: float
    value: float

    acquired_price: float
    acquired_value: float

    performance: Performance
