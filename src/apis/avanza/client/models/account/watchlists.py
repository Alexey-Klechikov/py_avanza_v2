from datetime import datetime

from pydantic import BaseModel, Field


class CustomerId(BaseModel):
    id: int


class UserId(BaseModel):
    customer_id: CustomerId = Field(alias="customerId")


class Watchlist(BaseModel):
    watchList_id: str = Field(alias="watchListId")
    orderbook_ids: list[str] = Field(alias="orderbookIds")
    created: datetime
    modified: datetime
    name: str
    url_name: str = Field(alias="urlName")
