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


class Order(BaseModel):
    account: Account
    order_id: str = Field(alias="orderId")
    volume: int
    price: float
    amount: float
    orderbook_id: str = Field(alias="orderbookId")
    side: str
    valid_until: datetime = Field(alias="validUntil")
    created: datetime
    deletable: bool
    modifiable: bool
    message: str
    state: str
    state_text: str = Field(alias="stateText")
    state_message: str = Field(alias="stateMessage")
    orderbook: Orderbook
    additional_parameters: dict = Field(alias="additionalParameters")


class FundOrder(BaseModel):
    account: Account
    order_id: str = Field(alias="orderId")
    volume: float | None = None
    amount: float
    orderbook_id: str = Field(alias="orderbookId")
    side: str
    valid_until: datetime = Field(alias="validUntil")
    created: datetime
    deletable: bool
    modifiable: bool
    message: str
    state: str
    state_text: str = Field(alias="stateText")
    state_message: str = Field(alias="stateMessage")
    orderbook: Orderbook
    additional_parameters: dict = Field(alias="additionalParameters")
    visible_on_account_date: str = Field(alias="visibleOnAccountDate")
    stop_time: str = Field(alias="stopTime")


class Orders(BaseModel):
    orders: list[Order]
    fund_orders: list[FundOrder] = Field(alias="fundOrders")
