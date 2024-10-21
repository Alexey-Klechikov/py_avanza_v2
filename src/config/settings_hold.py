from dataclasses import dataclass, field
from typing import List

from config.settings_base import BaseHold, BaseOMX
from services.hold_statistics.models import Scope


@dataclass
class HoldStatistics(BaseOMX, BaseHold):
    BUDGET: float = 1200
    SCOPES: List[Scope] = field(default_factory=lambda: [Scope.INTERDAY, Scope.INTRADAY])
