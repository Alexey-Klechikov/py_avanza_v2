from pydantic import BaseModel, Field, field_validator


class Price(BaseModel):
    last: float | None
    currency: str
    today_change_percent: float | None = Field(alias="todayChangePercent")
    today_change_value: float | None = Field(alias="todayChangeValue")
    today_change_direction: float | None = Field(alias="todayChangeDirection")
    three_months_ago_change_percent: float | None = Field(alias="threeMonthsAgoChangePercent")
    three_months_ago_change_direction: float | None = Field(alias="threeMonthsAgoChangeDirection")
    spread: float | None

    @field_validator(
        "today_change_percent",
        "today_change_value",
        "today_change_direction",
        "three_months_ago_change_percent",
        "three_months_ago_change_direction",
        "spread",
        "last",
        mode="before",
    )
    @classmethod
    def parse_float(cls, v):
        if v is None:
            return None

        if isinstance(v, str):
            v = v.replace(",", ".").replace("−", "-").replace("\xa0", "")

        return float(v)


class StockSector(BaseModel):
    id: int
    level: int
    name: str
    english_name: str = Field(alias="englishName")
    highlighted_name: str | None = Field(alias="highlightedName")


class Hit(BaseModel):
    type: str
    title: str
    description: str
    path: str | None
    flag_code: str = Field(alias="flagCode")
    order_book_id: str = Field(alias="orderBookId")
    url_slug_name: str = Field(alias="urlSlugName")
    tradeable: bool
    sellable: bool
    buyable: bool
    price: Price
    stock_sectors: list[StockSector] = Field(alias="stockSectors")
    fund_tags: list[dict] = Field(alias="fundTags")
    market_place_name: str = Field(alias="marketPlaceName")
    sub_type: str | None = Field(alias="subType")


class Pagination(BaseModel):
    size: int
    from_: int = Field(alias="from")


class SearchFilter(BaseModel):
    types: list[str]


class Facet(BaseModel):
    type: str
    count: int


class Facets(BaseModel):
    types: list[Facet]


class SearchResult(BaseModel):
    total_number_of_hits: int = Field(alias="totalNumberOfHits")
    hits: list[Hit]
    search_query: str = Field(alias="searchQuery")
    pagination: Pagination
    search_filter: SearchFilter = Field(alias="searchFilter")
    facets: Facets
