from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


def convert_timestamp_to_datetime(v: int | None):
    return datetime.fromtimestamp(v / 1000) if v is not None else None


class Listing(BaseModel):
    short_name: str = Field(alias="shortName")
    ticker_symbol: str = Field(alias="tickerSymbol")
    country_code: str = Field(alias="countryCode")
    currency: str
    market_place_code: str = Field(alias="marketPlaceCode")
    # market_place_name and market_trades_available are not present in test data
    tick_size_list_id: str = Field(alias="tickSizeListId")


class HistoricalClosingPrices(BaseModel):
    one_day: float = Field(alias="oneDay")
    one_week: float = Field(alias="oneWeek")
    one_month: float = Field(alias="oneMonth")
    three_months: float = Field(alias="threeMonths")
    start_of_year: float = Field(alias="startOfYear")
    one_year: float = Field(alias="oneYear")
    three_years: float = Field(alias="threeYears")
    five_years: float = Field(alias="fiveYears")
    ten_years: float = Field(alias="tenYears")
    start_date: date = Field(alias="startDate")
    start: float | None = Field(default=None, alias="start")


class Constituent(BaseModel):
    change_percent: float = Field(alias="changePercent")
    country_code: str = Field(alias="countryCode")
    name: str
    orderbook_id: str = Field(alias="orderbookId")


class KeyIndicators(BaseModel):
    number_of_owners: int = Field(alias="numberOfOwners")
    dividends_per_year: int = Field(alias="dividendsPerYear")


class Quote(BaseModel):
    last: float
    highest: float
    lowest: float
    change: float
    change_percent: float = Field(alias="changePercent")
    time_of_last: datetime = Field(alias="timeOfLast")
    total_value_traded: float = Field(alias="totalValueTraded")
    total_volume_traded: int = Field(alias="totalVolumeTraded")
    updated: datetime

    @field_validator("time_of_last", "updated", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        return convert_timestamp_to_datetime(v)


class Stock(BaseModel):
    preferred: bool
    depository_receipt: bool = Field(alias="depositoryReceipt")


class Company(BaseModel):
    company_id: str = Field(alias="companyId")
    description: str
    ceo: str
    chairman: str
    homepage: str


class CompanyOwners(BaseModel):
    owners: list[str]


class BrokerTradeSummary(BaseModel):
    broker_code: str = Field(alias="brokerCode")
    sell_volume: int = Field(alias="sellVolume")
    buy_volume: int = Field(alias="buyVolume")
    net_buy_volume: int = Field(alias="netBuyVolume")
    broker_name: str = Field(alias="brokerName")


class Dividends(BaseModel):
    events: list[str]
    past_events: list[str] = Field(alias="pastEvents")


class TradingTerms(BaseModel):
    collateral_value: float = Field(alias="collateralValue")
    margin_requirement: float = Field(alias="marginRequirement")
    short_sellable: bool = Field(alias="shortSellable")
    super_interest_approved: bool = Field(alias="superInterestApproved")


class Trade(BaseModel):
    buyer: str
    seller: str
    deal_time: datetime = Field(alias="dealTime")
    price: float
    volume: int
    matched_on_market: bool = Field(alias="matchedOnMarket")
    cancelled: bool

    @field_validator("deal_time", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        return convert_timestamp_to_datetime(v)


class InstrumentIndex(BaseModel):
    orderbook_id: str = Field(alias="orderbookId")
    name: str
    isin: str
    listing: Listing
    historical_closing_prices: HistoricalClosingPrices = Field(alias="historicalClosingPrices")
    quote: Quote
    type: str
    index_type: str = Field(alias="indexType")
    previous_closing_price: float = Field(alias="previousClosingPrice")
    description: str
    constituents: list[Constituent]
