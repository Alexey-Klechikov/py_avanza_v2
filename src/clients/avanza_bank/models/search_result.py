from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class Price(BaseModel):
    last: Optional[float]
    currency: str
    today_change_percent: Optional[float] = Field(alias="todayChangePercent")
    today_change_value: Optional[float] = Field(alias="todayChangeValue")
    today_change_direction: Optional[float] = Field(alias="todayChangeDirection")
    three_months_ago_change_percent: Optional[float] = Field(
        alias="threeMonthsAgoChangePercent",
    )
    three_months_ago_change_direction: Optional[float] = Field(
        alias="threeMonthsAgoChangeDirection",
    )
    spread: Optional[float]

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
    highlighted_name: Optional[str] = Field(alias="highlightedName")


class Hit(BaseModel):
    type: str
    title: str
    description: str
    path: Optional[str]
    flag_code: str = Field(alias="flagCode")
    order_book_id: str = Field(alias="orderBookId")
    url_slug_name: str = Field(alias="urlSlugName")
    tradeable: bool
    sellable: bool
    buyable: bool
    price: Price
    stock_sectors: List[StockSector] = Field(alias="stockSectors")
    fund_tags: List[dict] = Field(alias="fundTags")
    market_place_name: str = Field(alias="marketPlaceName")
    sub_type: Optional[str] = Field(alias="subType")


class Pagination(BaseModel):
    size: int
    from_: int = Field(alias="from")


class SearchFilter(BaseModel):
    types: List[str]


class Facet(BaseModel):
    type: str
    count: int


class Facets(BaseModel):
    types: List[Facet]


class SearchResult(BaseModel):
    total_number_of_hits: int = Field(alias="totalNumberOfHits")
    hits: List[Hit]
    search_query: str = Field(alias="searchQuery")
    pagination: Pagination
    search_filter: SearchFilter = Field(alias="searchFilter")
    facets: Facets
