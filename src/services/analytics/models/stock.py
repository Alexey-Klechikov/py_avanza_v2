from typing import List

from pydantic import BaseModel, Field

from apis.avanza.client.models.instrument.stock import CompanyEvent, DividendEvent


class Stock(BaseModel):
    name: str
    order_book_id: str

    company_events: List[CompanyEvent] = Field(default_factory=list)
    dividends: List[DividendEvent] = Field(default_factory=list)
