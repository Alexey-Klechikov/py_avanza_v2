from dataclasses import dataclass, field
from typing import List

from config.settings_base import BaseHoldCorrelation, BaseHoldStatistics, BaseOMX
from hold_statistics.models import Scope


@dataclass
class HoldStatistics(BaseOMX, BaseHoldStatistics):
    BUDGET: float = 1200
    SCOPES: List[Scope] = field(default_factory=lambda: [Scope.INTERDAY, Scope.INTRADAY])


@dataclass
class HoldCorrelation(BaseOMX, BaseHoldCorrelation):
    BUDGET: float = 1200
    SCOPES: List[Scope] = field(default_factory=lambda: [Scope.INTRADAY])
    MIN_DECIDING_PRICE_CHANGE: float = 2.0
