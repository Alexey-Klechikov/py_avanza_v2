from datetime import datetime

from pydantic import BaseModel, Field


class Account(BaseModel):
    account_id: str = Field(alias="accountId")
    name: dict
    type: dict
    url_parameter_id: str = Field(alias="urlParameterId")


class Orderbook(BaseModel):
    id: str
    name: str
    country_code: str = Field(alias="countryCode")
    currency: str
    instrument_type: str = Field(alias="instrumentType")
    volume_factor: str = Field(alias="volumeFactor")
    isin: str
    mic: str


class Deal(BaseModel):
    id: str
    account: Account
    orderbook_id: str = Field(alias="orderbookId")
    volume: int
    price: float
    amount: float
    time: datetime
    side: str
    order_id: str = Field(alias="orderId")
    orderbook: Orderbook


class Deals(BaseModel):
    deals: list[Deal]
