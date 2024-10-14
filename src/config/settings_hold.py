from dataclasses import dataclass, field
from typing import List

from config.settings_base import BaseHold, BaseOMX, BaseTrade
from services.hold.models import Scope


@dataclass
class HoldOMX_Main(BaseOMX, BaseHold):
    BUDGET: float = 1200
    SCOPES: List[Scope] = field(default_factory=lambda: [Scope.INTERDAY, Scope.INTRADAY])


@dataclass
class HoldOMX_DT(BaseOMX, BaseTrade):
    BUDGET: float = 1500
    SCOPES: List[Scope] = field(default_factory=lambda: [Scope.INTERDAY])
