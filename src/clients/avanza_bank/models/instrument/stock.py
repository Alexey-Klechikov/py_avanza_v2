from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import List, Optional

convert_timestamp_to_datetime = lambda v: (
    datetime.fromtimestamp(v / 1000) if v is not None else None
)


class Sector(BaseModel):
    sector_id: int = Field(alias="sectorId")
    sector_name: str = Field(alias="sectorName")


class Listing(BaseModel):
    short_name: str = Field(alias="shortName")
    ticker_symbol: str = Field(alias="tickerSymbol")
    country_code: str = Field(alias="countryCode")
    currency: str
    market_place_code: str = Field(alias="marketPlaceCode")
    market_place_name: str = Field(alias="marketPlaceName")
    tick_size_list_id: str = Field(alias="tickSizeListId")
    market_trades_available: bool = Field(alias="marketTradesAvailable")


class HistoricalClosingPrices(BaseModel):
    one_day: float = Field(alias="oneDay")
    one_week: float = Field(alias="oneWeek")
    one_month: float = Field(alias="oneMonth")
    three_months: float = Field(alias="threeMonths")
    start_of_year: Optional[float] = Field(alias="startOfYear")
    one_year: float = Field(alias="oneYear")
    start: float
    start_date: date = Field(alias="startDate")


class Capital(BaseModel):
    value: float
    currency: str


class Dividend(BaseModel):
    ex_date: date = Field(alias="exDate")
    amount: float
    currency_code: str = Field(alias="currencyCode")
    ex_date_status: str = Field(alias="exDateStatus")


class Report(BaseModel):
    date: date
    report_type: str = Field(alias="reportType")


class KeyIndicators(BaseModel):
    number_of_owners: int = Field(alias="numberOfOwners")
    report_date: date = Field(alias="reportDate")
    direct_yield: float = Field(alias="directYield")
    ordinary_direct_yield: float = Field(alias="ordinaryDirectYield")
    total_direct_yield: float = Field(alias="totalDirectYield")
    volatility: float
    beta: float
    price_earnings_ratio: float = Field(alias="priceEarningsRatio")
    price_sales_ratio: float = Field(alias="priceSalesRatio")
    ev_ebit_ratio: float = Field(alias="evEbitRatio")
    interest_coverage_ratio: float = Field(alias="interestCoverageRatio")
    return_on_equity: float = Field(alias="returnOnEquity")
    return_on_total_assets: float = Field(alias="returnOnTotalAssets")
    equity_ratio: float = Field(alias="equityRatio")
    capital_turnover: float = Field(alias="capitalTurnover")
    operating_profit_margin: float = Field(alias="operatingProfitMargin")
    gross_margin: float = Field(alias="grossMargin")
    net_margin: float = Field(alias="netMargin")
    market_capital: Capital = Field(alias="marketCapital")
    equity_per_share: Capital = Field(alias="equityPerShare")
    turnover_per_share: Capital = Field(alias="turnoverPerShare")
    earnings_per_share: Capital = Field(alias="earningsPerShare")
    dividend: Dividend
    dividends_per_year: int = Field(alias="dividendsPerYear")
    next_report: Report = Field(alias="nextReport")
    previous_report: Report = Field(alias="previousReport")


class Quote(BaseModel):
    buy: float
    sell: float
    last: float
    highest: float
    lowest: float
    change: float
    change_percent: float = Field(alias="changePercent")
    spread: float
    time_of_last: datetime = Field(alias="timeOfLast")
    total_value_traded: float = Field(alias="totalValueTraded")
    total_volume_traded: int = Field(alias="totalVolumeTraded")
    updated: int
    volume_weighted_average_price: float = Field(alias="volumeWeightedAveragePrice")

    @field_validator("time_of_last", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        return convert_timestamp_to_datetime(v)


class Stock(BaseModel):
    preferred: bool
    depository_receipt: bool = Field(alias="depositoryReceipt")
    number_of_shares: int = Field(alias="numberOfShares")


class Company(BaseModel):
    company_id: str = Field(alias="companyId")
    description: str
    ceo: str
    chairman: str
    total_number_of_shares: int = Field(alias="totalNumberOfShares")
    homepage: str


class CompanyEvent(BaseModel):
    date: date
    type: str


class CompanyEvents(BaseModel):
    events: List[CompanyEvent]


class CompanyOwner(BaseModel):
    name: str
    percent_of_capital: float = Field(alias="percentOfCapital")
    percent_of_votes: float = Field(alias="percentOfVotes")


class CompanyOwners(BaseModel):
    owners: List[CompanyOwner]
    updated: date


class BrokerTradeSummary(BaseModel):
    broker_code: str = Field(alias="brokerCode")
    sell_volume: int = Field(alias="sellVolume")
    buy_volume: int = Field(alias="buyVolume")
    net_buy_volume: int = Field(alias="netBuyVolume")
    broker_name: str = Field(alias="brokerName")


class DivivendEvent(BaseModel):
    ex_date: date = Field(alias="exDate")
    amount: float
    currency_code: str = Field(alias="currencyCode")
    dividend_type: str = Field(alias="dividendType")


class Dividends(BaseModel):
    events: List[DivivendEvent]
    past_events: List[DivivendEvent] = Field(alias="pastEvents")


class TradingTerms(BaseModel):
    collateral_value: float = Field(alias="collateralValue")
    margin_requirement: float = Field(alias="marginRequirement")
    short_sellable: bool = Field(alias="shortSellable")
    super_interest_approved: bool = Field(alias="superInterestApproved")


class FundExposure(BaseModel):
    orderbook_id: str = Field(alias="orderbookId")
    name: str
    exposure: float
    instrument_type: str = Field(alias="instrumentType")
    country_code: str = Field(alias="countryCode")
    has_position: bool = Field(alias="hasPosition")


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


class OrderDepthLevelSide(BaseModel):
    price: float
    price_string: str = Field(alias="priceString")
    volume: int


class OrderDepthLevel(BaseModel):
    buy_side: OrderDepthLevelSide = Field(alias="buySide")
    sell_side: OrderDepthLevelSide = Field(alias="sellSide")


class OrderDepth(BaseModel):
    received_time: datetime = Field(alias="receivedTime")
    levels: List[OrderDepthLevel]

    @field_validator("received_time", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        return convert_timestamp_to_datetime(v)


class InstrumentStock(BaseModel):
    orderbook_id: int = Field(alias="orderbookId")
    name: str
    isin: str
    instrument_id: int = Field(alias="instrumentId")
    sectors: List[Sector]
    tradable: str
    listing: Listing
    historical_closing_prices: HistoricalClosingPrices = Field(
        alias="historicalClosingPrices"
    )
    key_indicators: dict = Field(alias="keyIndicators")
    quote: Quote
    type: str
    stock: Stock
    company: Company
    company_events: CompanyEvents = Field(alias="companyEvents")
    company_owners: CompanyOwners = Field(alias="companyOwners")
    broker_trade_summaries: List[BrokerTradeSummary] = Field(
        alias="brokerTradeSummaries"
    )
    dividends: Dividends
    trading_terms: TradingTerms = Field(alias="tradingTerms")
    fund_exposures: List[FundExposure] = Field(alias="fundExposures")
    trades: List[Trade]
    order_depth: OrderDepth = Field(alias="orderDepth")
    order_depth_levels: List[dict] = Field(alias="orderDepthLevels")
