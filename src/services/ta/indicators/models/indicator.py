from enum import Enum
from typing import Callable, List, Optional

from pydantic import BaseModel


class Plot(BaseModel):
    columns: List[str]

    color: Optional[str] = None
    type: Optional[str] = None
    markersize: Optional[int] = None
    ylim: Optional[List[float]] = None
    secondary_y: Optional[bool] = None
    ylabel: Optional[str] = None

    def get_kwargs(self):
        return {
            k: v
            for k, v in {
                "color": self.color,
                "type": self.type,
                "markersize": self.markersize,
                "ylim": self.ylim,
                "secondary_y": self.secondary_y,
                "ylabel": None if not self.ylabel else self.ylabel.replace(" ", "\n"),
            }.items()
            if v
        }


class HorizontalLine(BaseModel):
    y: float
    color: str


class Panel(str, Enum):
    MAIN = "MAIN"
    SEPARATE = "SEPARATE"


class Plots(BaseModel):
    panel: Panel
    list: List[Plot]
    horizontal_lines: List[HorizontalLine] = []


class Signal(BaseModel):
    LONG: Optional[Callable] = None
    SHORT: Optional[Callable] = None
    EXIT: Optional[Callable] = None


class Indicator(BaseModel):
    columns: list[str]
    signal: Signal
    plots: Plots
