from dataclasses import dataclass, field
from datetime import time
from typing import List

from config.settings_base import BaseHold, BaseOMX


@dataclass
class HoldRule:
    orderbook_direction: str
    buy_time: time
    sell_time: time
    budget: float
    take_profit: float


@dataclass
class HoldOMX(BaseOMX, BaseHold):
    RULES: List[HoldRule] = field(
        default_factory=lambda: [
            HoldRule(
                orderbook_direction="BULL",
                buy_time=time(17, 0),
                sell_time=time(10, 10),
                budget=1300,
                take_profit=0.3,
            ),
        ],
    )
