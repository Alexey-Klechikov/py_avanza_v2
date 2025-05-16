from datetime import date, datetime
from typing import Any

from avanza.constants import TransactionsDetailsType
from pydantic import BaseModel, Field


class Account(BaseModel):
    id: str
    name: str
    type: str
    url_parameter_id: str = Field(alias="urlParameterId")


class Amount(BaseModel):
    decimal_precision: int = Field(alias="decimalPrecision")
    unit: str
    unit_type: str = Field(alias="unitType")
    value: float


class Orderbook(BaseModel):
    currency: str
    flag_code: str | None = Field(alias="flagCode")
    id: str
    isin: str
    marketplace: str
    name: str
    type: str
    volume_factor: float = Field(alias="volumeFactor")


class Transaction(BaseModel):
    account: Account
    amount: Amount
    availability_date: datetime | None = Field(alias="availabilityDate")
    backoffice_type: TransactionsDetailsType = Field(alias="backofficeType")
    backoffice_type_text: str = Field(alias="backofficeTypeText")
    cancel_date: datetime | None = Field(alias="cancelDate")
    cancelled: bool
    commission: Any
    currency_rate: Any = Field(alias="currencyRate")
    date: datetime
    description: str
    foreign_tax_rate: Any = Field(alias="foreignTaxRate")
    id: str
    instrument_name: str = Field(alias="instrumentName")
    intraday: bool
    isin: str
    note_id: str | None = Field(alias="noteId")
    on_credit_account: bool = Field(alias="onCreditAccount")
    orderbook: Orderbook | None
    price_in_traded_currency: Amount = Field(alias="priceInTradedCurrency")
    price_in_transaction_currency: Amount = Field(alias="priceInTransactionCurrency")
    result: Amount | None
    settlement_date: datetime | None = Field(alias="settlementDate")
    trade_date: datetime | None = Field(alias="tradeDate")
    type: TransactionsDetailsType
    volume: Amount
    volume_factor: float = Field(alias="volumeFactor")


class DateRange(BaseModel):
    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")


class TransactionsFilter(BaseModel):
    account_ids: str | None = Field(alias="accountIds")
    date_range: DateRange = Field(alias="dateRange")
    include_cancelled: bool = Field(alias="includeCancelled")
    isin: Any
    transaction_types: list[TransactionsDetailsType] | None = Field(alias="transactionTypes")


class TransactionsDetails(BaseModel):
    first_transaction_date: date = Field(alias="firstTransactionDate")
    transactions: list[Transaction]
    transactions_after_filtering: int = Field(alias="transactionsAfterFiltering")
    transactions_filter: TransactionsFilter = Field(alias="transactionsFilter")
