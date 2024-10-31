from dataclasses import dataclass, field
from datetime import time

from config.settings_base import BaseHoldCorrelation, BaseHoldStatistics, BaseOMX
from hold_statistics.models import Scope


@dataclass
class HoldStatistics(BaseOMX, BaseHoldStatistics):
    BUDGET: float = 1200
    SCOPES: list[Scope] = field(default_factory=lambda: [Scope.INTERDAY, Scope.INTRADAY])


@dataclass
class HoldCorrelation(BaseOMX, BaseHoldCorrelation):
    BUDGET: float = 2000
    SCOPES: list[Scope] = field(default_factory=lambda: [Scope.INTERDAY, Scope.INTRADAY])
    MIN_DECIDING_PRICE_CHANGE: float = 2.0
    TRADING_END: time = time(17, 5)
    TRADING_TAKE_PROFIT: float = 0.05
