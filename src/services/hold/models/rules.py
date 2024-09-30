from datetime import time
from enum import Enum
from typing import Any

from pydantic import BaseModel


class Action(Enum):
    BUY = "BUY"
    SELL = "SELL"


class Direction(Enum):
    BULL = "BULL"
    BEAR = "BEAR"


class HoldRule(BaseModel):
    orderbook_direction: Direction
    buy_time: time
    sell_time: time
    take_profit: float
    settings: Any


class Event(BaseModel):
    at: time
    orderbook_direction: Direction
    action: Action
    take_profit: float
    budget: int
    settings: Any
