from datetime import time
from enum import Enum
from typing import Any

from pydantic import BaseModel

from apis.avanza.trade.models import Direction


class Action(Enum):
    BUY = "BUY"
    SELL = "SELL"

    def __str__(self):
        return self.value


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
    budget: float
    settings: Any
