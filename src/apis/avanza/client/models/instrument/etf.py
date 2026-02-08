from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


def convert_timestamp_to_datetime(v: int | None):
    return datetime.fromtimestamp(v / 1000) if v is not None else None


class Exposure(BaseModel):
    country_code: str = Field(alias="countryCode")
    country_name: str = Field(alias="countryName")
    weight: float


class CountryExposures(BaseModel):
    exposures: list[Exposure]
    updated: date


class SectorExposure(BaseModel):
    sector: str
    weight: float


class SectorExposures(BaseModel):
    exposures: list[SectorExposure]
    updated: date


class FundExposure(BaseModel):
    country_code: str = Field(alias="countryCode")
    exposure: float
    has_position: bool = Field(alias="hasPosition")
    instrument_type: str = Field(alias="instrumentType")
    name: str
    orderbook_id: str = Field(alias="orderbookId")


class Listing(BaseModel):
    short_name: str = Field(alias="shortName")
    ticker_symbol: str = Field(alias="tickerSymbol")
    country_code: str = Field(alias="countryCode")
    currency: str
    market_place_code: str = Field(alias="marketPlaceCode")
    market_place_name: str = Field(alias="marketPlaceName")
    tick_size_list_id: str = Field(alias="tickSizeListId")
    market_trades_available: bool = Field(alias="marketTradesAvailable")


class Quote(BaseModel):
    buy: float | None = None
    sell: float | None = None
    last: float
    highest: float
    lowest: float
    change: float
    change_percent: float = Field(alias="changePercent")
    spread: float | None = None
    time_of_last: datetime = Field(alias="timeOfLast")
    total_value_traded: float = Field(alias="totalValueTraded")
    total_volume_traded: int = Field(alias="totalVolumeTraded")
    updated: datetime
    volume_weighted_average_price: float | None = Field(default=None, alias="volumeWeightedAveragePrice")
    is_real_time: bool = Field(alias="isRealTime")

    @field_validator("time_of_last", "updated", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        return convert_timestamp_to_datetime(v)


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
    start: float | None = Field(default=None, alias="start")
    start_date: date = Field(alias="startDate")


class KeyIndicators(BaseModel):
    direction: str
    leverage: float
    number_of_owners: int = Field(alias="numberOfOwners")
    historic_yield: float = Field(alias="historicYield")
    historic_yield_date: date = Field(alias="historicYieldDate")


class UnderlyingListing(BaseModel):
    short_name: str = Field(alias="shortName")
    ticker_symbol: str = Field(alias="tickerSymbol")
    country_code: str = Field(alias="countryCode")
    currency: str
    market_place_code: str = Field(alias="marketPlaceCode")
    market_place_name: str = Field(alias="marketPlaceName")
    tick_size_list_id: str = Field(alias="tickSizeListId")
    market_trades_available: bool = Field(alias="marketTradesAvailable")


class UnderlyingQuote(BaseModel):
    last: float
    highest: float
    lowest: float
    change: float
    change_percent: float = Field(alias="changePercent")
    time_of_last: datetime = Field(alias="timeOfLast")
    total_value_traded: float = Field(alias="totalValueTraded")
    total_volume_traded: int = Field(alias="totalVolumeTraded")
    updated: datetime
    is_real_time: bool = Field(alias="isRealTime")

    @field_validator("time_of_last", "updated", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        return convert_timestamp_to_datetime(v)


class Underlying(BaseModel):
    orderbook_id: str = Field(alias="orderbookId")
    name: str
    instrument_type: str = Field(alias="instrumentType")
    quote: UnderlyingQuote
    listing: UnderlyingListing
    previous_closing_price: float = Field(alias="previousClosingPrice")


class InstrumentETF(BaseModel):
    orderbook_id: str = Field(alias="orderbookId")
    name: str
    isin: str
    tradable: str
    listing: Listing
    market_place: dict = Field(alias="marketPlace")
    historical_closing_prices: HistoricalClosingPrices = Field(alias="historicalClosingPrices")
    key_indicators: KeyIndicators = Field(alias="keyIndicators")
    quote: Quote
    type: str
    asset_category: str = Field(alias="assetCategory")
    category: str
    issuer: str
    description: str
    documents: dict
    order_depth: dict = Field(alias="orderDepth")
    broker_trade_summaries: list = Field(alias="brokerTradeSummaries")
    fee: dict
    trades: list = Field(alias="trades")
    trading_unit: int = Field(alias="tradingUnit")
    collateral_value: float = Field(alias="collateralValue")
    super_interest_approved: bool = Field(alias="superInterestApproved")
    intro_date: date = Field(alias="introDate")
    dividends: dict
    fund_exposures: list[FundExposure] = Field(alias="fundExposures")
    risk_score: str = Field(alias="riskScore")
    holding_period: str = Field(alias="holdingPeriod")
    country_exposures: CountryExposures = Field(alias="countryExposures")
    sector_exposures: SectorExposures = Field(alias="sectorExposures")
    portfolio_date: date = Field(alias="portfolioDate")
    esg_view: dict = Field(alias="esgView")
    underlying: Underlying
