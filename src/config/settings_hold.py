from dataclasses import dataclass, field
from datetime import time
from typing import List

from config.settings_base import BaseHold, BaseOMX, BaseTrade


@dataclass
class HoldRule:
    orderbook_direction: str
    buy_time: time
    sell_time: time
    take_profit: float
    budget: float = 1300


@dataclass
class HoldOMX_Main(BaseOMX, BaseHold):
    RULES: List[HoldRule] = field(
        default_factory=lambda: [
            HoldRule(
                orderbook_direction="BULL",
                buy_time=time(17, 0),
                sell_time=time(10, 00),
                take_profit=0.3,
            ),
            HoldRule(
                orderbook_direction="BULL",
                buy_time=time(10, 20),
                sell_time=time(14, 30),
                take_profit=0.04,
            ),
            HoldRule(
                orderbook_direction="BULL",
                buy_time=time(14, 30),
                sell_time=time(16, 30),
                take_profit=0.12,
            ),
            HoldRule(
                orderbook_direction="BEAR",
                buy_time=time(12, 40),
                sell_time=time(16, 50),
                take_profit=0.18,
            ),
        ],
    )


@dataclass
class HoldOMX_DT(BaseOMX, BaseTrade):
    RULES: List[HoldRule] = field(
        default_factory=lambda: [
            HoldRule(
                orderbook_direction="BULL",
                buy_time=time(17, 2),
                sell_time=time(9, 40),
                take_profit=0.3,
                budget=1500,
            ),
        ],
    )
