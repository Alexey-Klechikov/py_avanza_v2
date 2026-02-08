from datetime import date, datetime

from pydantic import BaseModel, Field


class AdminCompany(BaseModel):
    country: str
    name: str
    url: str


class FundManager(BaseModel):
    name: str
    start_date: date = Field(alias="startDate")


class FundRating(BaseModel):
    date: datetime
    fund_rating: int = Field(alias="fundRating")
    fund_rating_type: str = Field(alias="fundRatingType")


class FundTradingTerms(BaseModel):
    bank_days_until_buy: str = Field(alias="bankDaysUntilBuy")
    bank_days_until_sell: str = Field(alias="bankDaysUntilSell")
    bank_days_until_visible_in_depot_when_buy: str = Field(alias="bankDaysUntilVisibleInDepotWhenBuy")
    bank_days_until_visible_in_depot_when_sell: str = Field(alias="bankDaysUntilVisibleInDepotWhenSell")
    buy_price_denominator: float | None = Field(alias="buyPriceDenominator")
    buy_stop_date_time: datetime = Field(alias="buyStopDateTime")
    fee_info: str | None = Field(alias="feeInfo")
    has_cash_dividends: bool = Field(alias="hasCashDividends")
    has_currency_exchange_fee: bool = Field(alias="hasCurrencyExchangeFee")
    lock_in_interval_in_months: int = Field(alias="lockInIntervalInMonths")
    minimum_buy: float = Field(alias="minimumBuy")
    minimum_buy_monthly_saving: float = Field(alias="minimumBuyMonthlySaving")
    minimum_threshold_additional_buy: float = Field(alias="minimumThresholdAdditionalBuy")
    orderbook_id: str = Field(alias="orderbookId")
    private_asset: bool = Field(alias="privateAsset")
    sell_stop_date_time: datetime = Field(alias="sellStopDateTime")
    trade_currency: str = Field(alias="tradeCurrency")
    trade_frequency: str = Field(alias="tradeFrequency")
    trading_info: str = Field(alias="tradingInfo")


class HoldingChartData(BaseModel):
    country_code: str | None = Field(alias="countryCode")
    currency: str | None
    delta_rank: int | None = Field(alias="deltaRank")
    isin: str | None
    name: str
    orderbook_id: str | None = Field(alias="orderbookId")
    previous_y: float = Field(alias="previousY")
    type: str | None
    y: float


class CountryChartData(BaseModel):
    country_code: str = Field(alias="countryCode")
    currency: str | None
    delta_rank: int | None = Field(alias="deltaRank")
    isin: str | None
    name: str
    orderbook_id: str | None = Field(alias="orderbookId")
    previous_y: float = Field(alias="previousY")
    type: str | None
    y: float


class SectorChartData(BaseModel):
    country_code: str | None = Field(alias="countryCode")
    currency: str | None
    delta_rank: int | None = Field(alias="deltaRank")
    isin: str | None
    name: str
    orderbook_id: str | None = Field(alias="orderbookId")
    previous_y: float = Field(alias="previousY")
    type: str | None
    y: float


class ProductInvolvement(BaseModel):
    name: str
    product: str
    product_description: str = Field(alias="productDescription")
    value: float


class RiskLevel(BaseModel):
    risk_number: int = Field(alias="riskNumber")
    risk_text: str = Field(alias="riskText")


class InstrumentFund(BaseModel):
    admin_company: AdminCompany = Field(alias="adminCompany")
    arctic_oil_and_gas_exploration_involvement: float = Field(alias="arcticOilAndGasExplorationInvolvement")
    aum_covered_carbon: float | None = Field(alias="aumCoveredCarbon")
    capital: float
    carbon_risk_score: float = Field(alias="carbonRiskScore")
    carbon_solutions_involvement: float | None = Field(alias="carbonSolutionsInvolvement")
    categories: list[str]
    collateral_value: float = Field(alias="collateralValue")
    controversy_score: float | None = Field(alias="controversyScore")
    country_chart_data: list[CountryChartData] = Field(alias="countryChartData")
    currency: str
    current_date_time: datetime = Field(alias="currentDateTime")
    description: str
    environmental_rating: int = Field(alias="environmentalRating")
    environmental_score: float = Field(alias="environmentalScore")
    esg_score: float = Field(alias="esgScore")
    eu_article_type: dict = Field(alias="euArticleType")
    excluded_from_promotion: bool = Field(alias="excludedFromPromotion")
    fossil_fuel_involvement: float | None = Field(alias="fossilFuelInvolvement")
    fund_managers: list[FundManager] = Field(alias="fundManagers")
    fund_ratings: list[FundRating] = Field(alias="fundRatings")
    fund_trading_terms: FundTradingTerms = Field(alias="fundTradingTerms")
    fund_type: str = Field(alias="fundType")
    fund_type_name: str = Field(alias="fundTypeName")
    governance_rating: int = Field(alias="governanceRating")
    governance_score: float = Field(alias="governanceScore")
    hedge_fund: bool = Field(alias="hedgeFund")
    holding_chart_data: list[HoldingChartData] = Field(alias="holdingChartData")
    index_fund: bool = Field(alias="indexFund")
    isin: str
    low_carbon: bool = Field(alias="lowCarbon")
    managed_type: str = Field(alias="managedType")
    management_fee: float = Field(alias="managementFee")
    name: str
    nav: float
    nav_date: datetime = Field(alias="navDate")
    oil_and_gas_production_involvement: float | None = Field(alias="oilAndGasProductionInvolvement")
    oil_sands_extraction_involvement: float = Field(alias="oilSandsExtractionInvolvement")
    portfolio_date: date = Field(alias="portfolioDate")
    ppm_code: str = Field(alias="ppmCode")
    previous_portfolio_date: date = Field(alias="previousPortfolioDate")
    pricing_frequency: str = Field(alias="pricingFrequency")
    primary_benchmark: str = Field(alias="primaryBenchmark")
    product_involvements: list[ProductInvolvement] = Field(alias="productInvolvements")
    rating: int
    recommended_holding_period: str = Field(alias="recommendedHoldingPeriod")
    risk_level: RiskLevel = Field(alias="riskLevel")
    sector_chart_data: list[SectorChartData] = Field(alias="sectorChartData")
    sharpe_ratio: float = Field(alias="sharpeRatio")
    social_rating: int = Field(alias="socialRating")
    social_score: float = Field(alias="socialScore")
    standard_deviation: float = Field(alias="standardDeviation")
    start_date: date = Field(alias="startDate")
    sustainability_development_goals: list[dict] = Field(alias="sustainabilityDevelopmentGoals")
    sustainability_rating: int = Field(alias="sustainabilityRating")
    sustainability_rating_category_name: str = Field(alias="sustainabilityRatingCategoryName")
    svanen: bool
    thermal_coal_involvement: float = Field(alias="thermalCoalInvolvement")
    thermal_coal_power_generation_involvement: float | None = Field(alias="thermalCoalPowerGenerationInvolvement")
    ucits_fund: bool = Field(alias="ucitsFund")
