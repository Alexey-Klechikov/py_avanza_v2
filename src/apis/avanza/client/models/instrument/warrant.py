from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


def convert_timestamp_to_datetime(v: int | None):
    return datetime.fromtimestamp(v / 1000) if v is not None else None


class MarketMakerHistoricalClosingPrices(BaseModel):
    one_day: float | None = Field(alias="oneDay", default=None)
    one_week: float | None = Field(alias="oneWeek", default=None)
    one_month: float | None = Field(alias="oneMonth", default=None)
    start: float | None = Field(default=None)
    start_date: date | None = Field(alias="startDate", default=None)


class HistoricalClosingPrices(BaseModel):
    one_day: float | None = Field(alias="oneDay", default=None)
    one_week: float | None = Field(alias="oneWeek", default=None)
    one_month: float | None = Field(alias="oneMonth", default=None)
    three_months: float | None = Field(alias="threeMonths", default=None)
    six_months: float | None = Field(alias="sixMonths", default=None)
    start: float | None = Field(default=None)
    start_date: date = Field(alias="startDate", default_factory=date.today)
    market_maker: MarketMakerHistoricalClosingPrices | None = Field(alias="marketMaker", default=None)


class Listing(BaseModel):
    short_name: str = Field(alias="shortName")
    ticker_symbol: str = Field(alias="tickerSymbol")
    country_code: str = Field(alias="countryCode")
    currency: str
    market_place_code: str = Field(alias="marketPlaceCode")
    market_place_name: str = Field(alias="marketPlaceName")
    tick_size_list_id: str = Field(alias="tickSizeListId")
    market_trades_available: bool = Field(alias="marketTradesAvailable")


class KeyIndicators(BaseModel):
    parity: float
    barrier_level: float = Field(alias="barrierLevel")
    financing_level: float = Field(alias="financingLevel")
    direction: str
    strike_price: float | None = Field(alias="strikePrice", default=None)
    leverage: float = Field(default=0.0)
    number_of_owners: int = Field(alias="numberOfOwners")
    sub_type: str = Field(alias="subType")
    is_aza: bool = Field(alias="isAza")


class MarketMakerQuote(BaseModel):
    current_buy_price: float | None = Field(alias="currentBuyPrice", default=None)
    current_sell_price: float | None = Field(alias="currentSellPrice", default=None)
    closing_price: float | None = Field(alias="closingPrice", default=None)
    latest_buy_price: float | None = Field(alias="latestBuyPrice", default=None)
    latest_buy_price_updated: int | None = Field(alias="latestBuyPriceUpdated", default=None)
    latest_sell_price: float | None = Field(alias="latestSellPrice", default=None)
    spread: float | None = Field(default=None)
    updated: int | None = Field(default=None)


class Quote(BaseModel):
    buy: float | None = Field(default=None)
    sell: float | None = Field(default=None)
    last: float
    highest: float | None = Field(default=None)
    lowest: float | None = Field(default=None)
    change: float
    change_percent: float = Field(alias="changePercent")
    spread: float | None = Field(default=None)
    time_of_last: datetime = Field(alias="timeOfLast")
    total_value_traded: float = Field(alias="totalValueTraded")
    total_volume_traded: int = Field(alias="totalVolumeTraded")
    updated: int
    volume_weighted_average_price: float | None = Field(alias="volumeWeightedAveragePrice", default=None)
    is_real_time: bool | None = Field(alias="isRealTime", default=None)
    market_maker_quote: MarketMakerQuote | None = Field(alias="marketMakerQuote", default=None)

    @field_validator("time_of_last", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        return convert_timestamp_to_datetime(v)


class Underlying(BaseModel):
    orderbook_id: str = Field(alias="orderbookId")
    name: str
    instrument_type: str = Field(alias="instrumentType")
    instrument_sub_type: str | None = Field(alias="instrumentSubType", default=None)
    quote: Quote
    listing: Listing
    previous_closing_price: float | None = Field(alias="previousClosingPrice", default=None)
    reference: bool | None = Field(default=None)


class Documents(BaseModel):
    kid: str
    prospectus: str


class OrderDepthLevelSide(BaseModel):
    price: float
    price_string: str = Field(alias="priceString")
    volume: float


class OrderDepthLevel(BaseModel):
    buy_side: OrderDepthLevelSide = Field(alias="buySide")
    sell_side: OrderDepthLevelSide = Field(alias="sellSide")


class OrderDepth(BaseModel):
    received_time: int = Field(alias="receivedTime")
    levels: list[OrderDepthLevel]
    market_maker_level_in_bid: int | None = Field(alias="marketMakerLevelInBid", default=None)
    market_maker_level_in_ask: int | None = Field(alias="marketMakerLevelInAsk", default=None)


class BrokerTradeSummary(BaseModel):
    broker_code: str = Field(alias="brokerCode")
    sell_volume: int = Field(alias="sellVolume")
    buy_volume: int = Field(alias="buyVolume")
    net_buy_volume: int = Field(alias="netBuyVolume")
    broker_name: str = Field(alias="brokerName")


class Fee(BaseModel):
    total_monetary_fee: float = Field(alias="totalMonetaryFee")
    total_percentage_fee: float = Field(alias="totalPercentageFee")


class Trade(BaseModel):
    buyer: str
    buyer_name: str = Field(alias="buyerName")
    seller: str
    seller_name: str = Field(alias="sellerName")
    deal_time: datetime = Field(alias="dealTime")
    price: float
    volume: int
    matched_on_market: bool = Field(alias="matchedOnMarket")
    cancelled: bool

    @field_validator("deal_time", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        return convert_timestamp_to_datetime(v)


class InstrumentWarrant(BaseModel):
    orderbook_id: str = Field(alias="orderbookId")
    name: str
    isin: str
    tradable: str
    listing: Listing
    historical_closing_prices: HistoricalClosingPrices = Field(alias="historicalClosingPrices")
    key_indicators: KeyIndicators = Field(alias="keyIndicators")
    quote: Quote
    type: str
    underlying: Underlying | None = Field(default=None)
    asset_category: str | None = Field(alias="assetCategory", default=None)
    category: str | None = Field(default=None)
    sub_category: str | None = Field(alias="subCategory", default=None)
    issuer: str
    documents: Documents
    order_depth: OrderDepth = Field(alias="orderDepth")
    broker_trade_summaries: list[BrokerTradeSummary] = Field(alias="brokerTradeSummaries")
    fee: Fee | None = Field(default=None)
    trades: list[Trade]
    trading_unit: int = Field(alias="tradingUnit")
    collateral_value: float = Field(alias="collateralValue")
