from pydantic import BaseModel, Field


class Value(BaseModel):
    value: float
    unit: str
    unit_type: str = Field(alias="unitType")
    decimal_precision: int = Field(alias="decimalPrecision")


class CurrencyBalance(BaseModel):
    balance: Value


class TotalValue(BaseModel):
    total_value: Value = Field(alias="totalValue")
    position_value: Value = Field(alias="positionValue")
    balance_on_trading_accounts: Value = Field(alias="balanceOnTradingAccounts")
    balance_on_savings_accounts: Value = Field(alias="balanceOnSavingsAccounts")
    accrued_interest: Value = Field(alias="accruedInterest")
    accrued_credit_interest: Value = Field(alias="accruedCreditInterest")
    accrued_debit_interest: Value = Field(alias="accruedDebitInterest")
    forward_balance: Value = Field(alias="forwardBalance")
    currency_balances: list[CurrencyBalance] = Field(alias="currencyBalances")


class Development(BaseModel):
    absolute: Value
    relative: Value


class TotalDevelopment(BaseModel):
    one_week: Development = Field(alias="ONE_WEEK")
    one_month: Development = Field(alias="ONE_MONTH")
    three_months: Development = Field(alias="THREE_MONTHS")
    this_year: Development = Field(alias="THIS_YEAR")
    one_year: Development = Field(alias="ONE_YEAR")
    three_years: Development = Field(alias="THREE_YEARS")
    all_time: Development = Field(alias="ALL_TIME")


class BuyingPower(BaseModel):
    total: Value
    total_excluding_credit: Value = Field(alias="totalExcludingCredit")
    balance_on_tradable_accounts: Value = Field(alias="balanceOnTradableAccounts")
    current_orders: Value = Field(alias="currentOrders")
    available_credit: Value = Field(alias="availableCredit")
    total_margin_requirement: Value = Field(alias="totalMarginRequirement")
    forward_result: Value = Field(alias="forwardResult")
    gross_exposure_limit: Value = Field(alias="grossExposureLimit")
    gross_exposure: Value = Field(alias="grossExposure")
    negative_accrued_interest: Value = Field(alias="negativeAccruedInterest")
    currency_balances: list[CurrencyBalance] = Field(alias="currencyBalances")


class Info(BaseModel):
    id: str
    type: str
    name: str
    url_parameter_id: str = Field(alias="urlParameterId")
    has_credit: bool = Field(alias="hasCredit")


class Account(BaseModel):
    info: Info
    tradable: bool
    total_value: TotalValue = Field(alias="totalValue")
    buying_power: BuyingPower = Field(alias="buyingPower")
    is_tradable: bool = Field(alias="isTradable")


class AccountOverview(BaseModel):
    total_value: TotalValue = Field(alias="totalValue")
    total_development: TotalDevelopment = Field(alias="totalDevelopment")
    buying_power: BuyingPower = Field(alias="buyingPower")
    has_credit: bool = Field(alias="hasCredit")
    accounts: list[Account]
