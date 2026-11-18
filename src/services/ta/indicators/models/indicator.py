import builtins
from collections.abc import Callable
from enum import Enum

from pydantic import BaseModel


class Plot(BaseModel):
    columns: list[str]

    color: str | None = None
    type: str | None = None
    markersize: int | None = None
    ylim: list[float] | None = None
    secondary_y: bool | None = None
    ylabel: str | None = None

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
    list: builtins.list[Plot]  # the field name shadows the builtin inside this class
    horizontal_lines: builtins.list[HorizontalLine] = []


class Signal(BaseModel):
    LONG: Callable | None = None
    SHORT: Callable | None = None
    EXIT: Callable | None = None


class Indicator(BaseModel):
    columns: list[str]
    signal: Signal
    plots: Plots
