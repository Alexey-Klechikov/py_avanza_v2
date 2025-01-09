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
    market_place_name: str = Field(alias="marketPlaceName")
    tick_size_list_id: str = Field(alias="tickSizeListId")
    market_trades_available: bool = Field(alias="marketTradesAvailable")


class HistoricalClosingPrices(BaseModel):
    one_day: float | None = Field(alias="oneDay", default=None)
    one_week: float | None = Field(alias="oneWeek", default=None)
    one_month: float | None = Field(alias="oneMonth", default=None)
    three_months: float | None = Field(alias="threeMonths", default=None)
    start_of_year: float | None = Field(alias="startOfYear", default=None)
    one_year: float = Field(alias="oneYear", default=None)
    start_date: date = Field(alias="startDate", default=datetime.now().date())


class KeyIndicators(BaseModel):
    leverage: float
    product_link: str = Field(alias="productLink")
    number_of_owners: int = Field(alias="numberOfOwners")
    is_aza: bool = Field(alias="isAza")


class Quote(BaseModel):
    buy: float = Field(default=None)
    sell: float = Field(default=None)
    last: float
    highest: float | None = Field(default=None)
    lowest: float | None = Field(default=None)
    change: float
    change_percent: float = Field(alias="changePercent")
    spread: float = Field(default=None)
    time_of_last: datetime = Field(alias="timeOfLast")
    total_value_traded: float = Field(alias="totalValueTraded")
    total_volume_traded: int = Field(alias="totalVolumeTraded")
    updated: datetime

    @field_validator("time_of_last", "updated", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        return convert_timestamp_to_datetime(v)


class Documents(BaseModel):
    kid: str
    prospectus: str


class Fee(BaseModel):
    total_monetary_fee: float = Field(alias="totalMonetaryFee")
    total_percentage_fee: float = Field(alias="totalPercentageFee")


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
    levels: list[OrderDepthLevel]
    market_maker_level_in_bid: int | None = Field(
        alias="marketMakerLevelInBid",
        default=None,
    )
    market_maker_level_in_ask: int | None = Field(
        alias="marketMakerLevelInAsk",
        default=None,
    )

    @field_validator("received_time", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        return convert_timestamp_to_datetime(v)


class BrokerTradeSummaries(BaseModel):
    broker_code: str = Field(alias="brokerCode")
    sell_volume: int = Field(alias="sellVolume")
    buy_volume: int = Field(alias="buyVolume")
    net_buy_volume: int = Field(alias="netBuyVolume")
    broker_name: str = Field(alias="brokerName")


class Underlying(BaseModel):
    orderbook_id: int = Field(alias="orderbookId")
    name: str
    instrument_type: str = Field(alias="instrumentType")
    instrument_sub_type: str = Field(alias="instrumentSubType")
    quote: Quote
    listing: Listing
    previous_closing_price: float = Field(alias="previousClosingPrice")


class InstrumentCertificate(BaseModel):
    orderbook_id: int = Field(alias="orderbookId")
    name: str
    isin: str
    tradable: str
    listing: Listing
    historical_closing_prices: HistoricalClosingPrices = Field(alias="historicalClosingPrices")
    key_indicators: KeyIndicators = Field(alias="keyIndicators")
    quote: Quote
    type: str
    underlying: Underlying
    asset_category: str | None = Field(alias="assetCategory", default=None)
    category: str | None = Field(default=None)
    sub_category: str | None = Field(alias="subCategory", default=None)
    issuer: str
    direction: str
    leverage: float
    documents: Documents
    fee: Fee
    trades: list[Trade]
    order_depth: OrderDepth = Field(alias="orderDepth")
    broker_trade_summaries: list[BrokerTradeSummaries] = Field(
        alias="brokerTradeSummaries",
    )
    collateral_value: float = Field(alias="collateralValue")
