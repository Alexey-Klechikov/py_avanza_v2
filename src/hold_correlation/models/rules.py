from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum
from typing import Any

from pydantic import BaseModel


class Correlation(Enum):
    SAME = "SAME"
    OPPOSITE = "OPPOSITE"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Interval:
    start: time
    end: time

    def __str__(self):
        return f"{self.start.strftime('%H:%M')} - {self.end.strftime('%H:%M')}"

    def duration_min(self):
        return (
            datetime.combine(datetime.today(), self.end) - datetime.combine(datetime.today(), self.start)
        ).seconds / 60


class HoldRuleCorrelation(BaseModel):
    deciding_interval: Interval
    action_interval: Interval
    correlation: Correlation
    efficiency: float
    multiplier: float
    settings: Any = None

    def __str__(self) -> str:
        return (
            f"{self.deciding_interval} ---> {self.action_interval}, "
            + f"corr. {self.correlation}, eff. {self.efficiency}, mult. {self.multiplier}"
        )

    def dump_dict(self):
        return {
            "deciding_interval": {
                "start": self.deciding_interval.start.strftime("%H:%M"),
                "end": self.deciding_interval.end.strftime("%H:%M"),
            },
            "action_interval": {
                "start": self.action_interval.start.strftime("%H:%M"),
                "end": self.action_interval.end.strftime("%H:%M"),
            },
            "correlation": self.correlation.value,
            "efficiency": round(self.efficiency, 2),
            "multiplier": round(self.multiplier, 2),
        }
