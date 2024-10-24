from datetime import datetime

from pydantic import BaseModel, Field


class Account(BaseModel):
    id: str
    type: str
    name: str
    url_parameter_id: str = Field(alias="urlParameterId")
    has_credit: bool = Field(alias="hasCredit")


class Value(BaseModel):
    value: float
    unit: str
    unit_type: str = Field(alias="unitType")
    decimal_precision: int = Field(alias="decimalPrecision")


class Quote(BaseModel):
    highest: Value | None
    lowest: Value | None
    buy: Value | None
    sell: Value | None
    latest: Value
    change: Value
    change_percent: Value = Field(alias="changePercent")
    updated: datetime | None


class Turnover(BaseModel):
    volume: Value | None
    value: Value | None


class LastDeal(BaseModel):
    date: datetime
    time: datetime | None


class Orderbook(BaseModel):
    id: str
    flag_code: str | None = Field(alias="flagCode")
    name: str
    type: str
    trade_status: str = Field(alias="tradeStatus")
    quote: Quote
    turnover: Turnover
    last_deal: dict | None = Field(alias="lastDeal")


class Instrument(BaseModel):
    id: str
    type: str
    name: str
    orderbook: Orderbook
    currency: str
    isin: str
    volume_factor: float = Field(alias="volumeFactor")


class LastTradingDayPerformance(BaseModel):
    absolute: Value
    relative: Value


class WithOrderbookPosition(BaseModel):
    account: Account
    instrument: Instrument
    volume: Value
    value: Value
    average_acquired_price: Value = Field(alias="averageAcquiredPrice")
    average_acquired_price_instrument_currency: Value = Field(
        alias="averageAcquiredPriceInstrumentCurrency",
    )
    acquired_value: Value = Field(alias="acquiredValue")
    last_trading_day_performance: LastTradingDayPerformance | None = Field(
        alias="lastTradingDayPerformance",
    )
    collateral_factor: Value = Field(alias="collateralFactor")
    super_interest_approved: bool = Field(alias="superInterestApproved")
    id: str


class CashPosition(BaseModel):
    account: Account
    total_balance: Value = Field(alias="totalBalance")
    id: str


class AccountsPositions(BaseModel):
    with_orderbook: list[WithOrderbookPosition] = Field(alias="withOrderbook")
    without_orderbook: list = Field(alias="withoutOrderbook")
    cash_positions: list[CashPosition] = Field(alias="cashPositions")
    with_credit_account: bool = Field(alias="withCreditAccount")
