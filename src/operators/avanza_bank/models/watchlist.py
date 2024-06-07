from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class Orderbook(BaseModel):
    id: str
    name: str
    spread: Optional[float]
    buy: Optional[float]
    sell: Optional[float]
    leverage: float
    start_date: date


class Watchlist(BaseModel):
    orderbooks: List[Orderbook]
    active_instrument: Optional[Orderbook] = None
