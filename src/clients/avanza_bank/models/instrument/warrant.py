from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import List, Optional

convert_timestamp_to_datetime = lambda v: (
    datetime.fromtimestamp(v / 1000) if v is not None else None
)


class HistoricalClosingPrices(BaseModel):
    one_day: Optional[float] = Field(alias="oneDay", default=None)
    one_week: Optional[float] = Field(alias="oneWeek", default=None)
    one_month: Optional[float] = Field(alias="oneMonth", default=None)
    start: float
    start_date: date = Field(alias="startDate")


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
    leverage: float = Field(default=0.0)
    number_of_owners: int = Field(alias="numberOfOwners")
    sub_type: str = Field(alias="subType")
    is_aza: bool = Field(alias="isAza")


class Quote(BaseModel):
    buy: float = Field(default=None)
    sell: float = Field(default=None)
    last: float
    highest: Optional[float] = Field(default=None)
    lowest: Optional[float] = Field(default=None)
    change: float
    change_percent: float = Field(alias="changePercent")
    spread: float = Field(default=None)
    time_of_last: datetime = Field(alias="timeOfLast")
    total_value_traded: float = Field(alias="totalValueTraded")
    total_volume_traded: int = Field(alias="totalVolumeTraded")
    updated: int
    volume_weighted_average_price: float = Field(alias="volumeWeightedAveragePrice")

    @field_validator("time_of_last", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        return convert_timestamp_to_datetime(v)


class Underlying(BaseModel):
    orderbook_id: str = Field(alias="orderbookId")
    name: str
    instrument_type: str = Field(alias="instrumentType")
    instrument_sub_type: str = Field(alias="instrumentSubType")
    quote: Quote
    listing: Listing
    previous_closing_price: float = Field(alias="previousClosingPrice")


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
    levels: List[OrderDepthLevel]
    market_maker_level_in_bid: Optional[int] = Field(
        alias="marketMakerLevelInBid", default=None
    )
    market_maker_level_in_ask: Optional[int] = Field(
        alias="marketMakerLevelInAsk", default=None
    )


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
    historical_closing_prices: HistoricalClosingPrices = Field(
        alias="historicalClosingPrices"
    )
    key_indicators: KeyIndicators = Field(alias="keyIndicators")
    quote: Quote
    type: str
    underlying: dict
    issuer: str
    documents: Documents
    order_depth: OrderDepth = Field(alias="orderDepth")
    broker_trade_summaries: List[BrokerTradeSummary] = Field(
        alias="brokerTradeSummaries"
    )
    fee: Fee
    trades: List[Trade]
    trading_unit: int = Field(alias="tradingUnit")
    collateral_value: float = Field(alias="collateralValue")
