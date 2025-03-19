from datetime import date

from pydantic import BaseModel, Field


class _MinMax(BaseModel):
    max_value: float = Field(alias="maxValue")
    min_value: float = Field(alias="minValue")


class Filter(BaseModel):
    country_codes: list[str] = Field(alias="countryCodes")
    market_place_codes: list[str] = Field(alias="marketPlaceCodes")
    market_places: list[str] = Field(alias="marketPlaces")
    sectors: list[str]


class CountryCode(BaseModel):
    display_name: str = Field(alias="displayName")
    number_of_orderbooks: int = Field(alias="numberOfOrderbooks")
    value: str


class FilterOptions(BaseModel):
    beta: _MinMax
    country_codes: list[CountryCode] = Field(alias="countryCodes")
    direct_yield_ratio: _MinMax = Field(alias="directYieldRatio")
    ev_ebit: _MinMax = Field(alias="evEbit")
    market_capitalization: _MinMax = Field(alias="marketCapitalization")
    market_places: list[dict] = Field(alias="marketPlaces")
    net_debt_ebitda_ratio: _MinMax = Field(alias="netDebtEbitdaRatio")
    number_of_owners: _MinMax = Field(alias="numberOfOwners")
    price_book_ratio: _MinMax = Field(alias="priceBookRatio")
    price_earnings_ratio: _MinMax = Field(alias="priceEarningsRatio")
    price_sales_ratio: _MinMax = Field(alias="priceSalesRatio")
    return_on_equity: _MinMax = Field(alias="returnOnEquity")
    sectors: list[dict]
    volatility: _MinMax


class Pagination(BaseModel):
    limit: int
    offset: int


class SortBy(BaseModel):
    order: str
    field: str


class Stock(BaseModel):
    beta: float | None = Field(default=None)
    buy_price: float | None = Field(alias="buyPrice", default=None)
    collateral_value: float = Field(alias="collateralValue")
    country_code: str = Field(alias="countryCode")
    currency: str
    direct_yield: float | None = Field(alias="directYield", default=None)
    dividend_per_share: float | None = Field(alias="dividendPerShare", default=None)
    dividend_ratio: float | None = Field(alias="dividendRatio", default=None)
    dividends_per_year: int | None = Field(alias="dividendsPerYear", default=None)
    earnings_per_share: float | None = Field(alias="earningsPerShare", default=None)
    equity_per_share: float | None = Field(alias="equityPerShare", default=None)
    ev_ebit_ratio: float | None = Field(alias="evEbitRatio", default=None)
    five_years_change_percent: float | None = Field(alias="fiveYearsChangePercent", default=None)
    has_analysis: bool = Field(alias="hasAnalysis")
    has_position: bool = Field(alias="hasPosition")
    highest_price: float | None = Field(alias="highestPrice", default=None)
    infinity_change_percent: float | None = Field(alias="infinityChangePercent", default=None)
    last_price: float | None = Field(alias="lastPrice", default=None)
    last_price_updated: int = Field(alias="lastPriceUpdated")
    lowest_price: float | None = Field(alias="lowestPrice", default=None)
    market_capitalization: float | None = Field(alias="marketCapitalization", default=None)
    market_place_code: str = Field(alias="marketPlaceCode")
    name: str
    net_debt_ebitda_ratio: float | None = Field(alias="netDebtEbitdaRatio", default=None)
    next_company_report: date | None = Field(alias="nextCompanyReport", default=None)
    next_dividend: date | None = Field(alias="nextDividend", default=None)
    number_of_owners: int = Field(alias="numberOfOwners")
    one_day_change_percent: float | None = Field(alias="oneDayChangePercent", default=None)
    one_month_change_percent: float | None = Field(alias="oneMonthChangePercent", default=None)
    one_week_change_percent: float | None = Field(alias="oneWeekChangePercent", default=None)
    one_year_change_percent: float | None = Field(alias="oneYearChangePercent", default=None)
    order_book_id: str = Field(alias="orderbookId")
    price_book_ratio: float | None = Field(alias="priceBookRatio", default=None)
    price_earnings_ratio: float | None = Field(alias="priceEarningsRatio", default=None)
    return_on_equity: float | None = Field(alias="returnOnEquity", default=None)
    rsi14: float | None = Field(alias="rsi14", default=None)
    rsi_trend_five_days: float | None = Field(alias="rsiTrendFiveDays", default=None)
    rsi_trend_three_days: float | None = Field(alias="rsiTrendThreeDays", default=None)
    sell_price: float | None = Field(alias="sellPrice", default=None)
    short_name: str = Field(alias="shortName")
    short_selling_ratio: float | None = Field(alias="shortSellingRatio", default=None)
    six_months_change_percent: float | None = Field(alias="sixMonthsChangePercent", default=None)
    sma20: float | None = Field(default=None)
    sma200: float | None = Field(default=None)
    sma50: float | None = Field(default=None)
    sma_between_50_and_200: float | None = Field(alias="smaBetween50and200", default=None)
    start_of_year_change_percent: float | None = Field(alias="startOfYearChangePercent", default=None)
    ten_years_change_percent: float | None = Field(alias="tenYearsChangePercent", default=None)
    three_months_change_percent: float | None = Field(alias="threeMonthsChangePercent", default=None)
    three_years_change_percent: float | None = Field(alias="threeYearsChangePercent", default=None)
    total_value_traded: float = Field(alias="totalValueTraded")
    total_volume_traded: float = Field(alias="totalVolumeTraded")
    turnover_per_share: float | None = Field(alias="turnoverPerShare", default=None)
    type: str
    volatility: float | None = Field(default=None)


class MarketStocksFilterResult(BaseModel):
    filter: Filter
    filter_options: FilterOptions = Field(alias="filterOptions")
    pagination: Pagination
    sort_by: SortBy = Field(alias="sortBy")
    stocks: list[Stock]
    total_number_of_orderbooks: int = Field(alias="totalNumberOfOrderbooks")
