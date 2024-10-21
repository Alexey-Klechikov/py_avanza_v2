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


class HoldRuleStatistics(BaseModel):
    orderbook_direction: Direction
    buy_time: time
    sell_time: time
    take_profit: float
    settings: Any

    def dump_dict(self):
        return {
            "orderbook_direction": self.orderbook_direction.value,
            "buy_time": self.buy_time.strftime("%H:%M"),
            "sell_time": self.sell_time.strftime("%H:%M"),
            "take_profit": round(self.take_profit, 2),
        }


class Event(BaseModel):
    at: time
    orderbook_direction: Direction
    action: Action
    take_profit: float
    budget: int
    settings: Any
