from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from services.trading.tracked_position import TrackedPosition

Side = Literal["LONG", "SHORT"]
SIDES_WITH_OPPOSITE: tuple[tuple[Side, Side], ...] = (("LONG", "SHORT"), ("SHORT", "LONG"))


@dataclass(frozen=True)
class ClosedTrade:
    capital_return: float  # fraction of the capital in the position


class Wallet(BaseModel):
    """Simulated holdings: at most one position per side."""

    long: TrackedPosition | None = None
    short: TrackedPosition | None = None

    def get(self, side: Side) -> TrackedPosition | None:
        return self.long if side == "LONG" else self.short

    def set(self, side: Side, position: TrackedPosition | None) -> None:
        if side == "LONG":
            self.long = position
        else:
            self.short = position

    def is_empty(self) -> bool:
        return self.long is None and self.short is None

    def close(self, side: Side, exit_price: float) -> ClosedTrade:
        position = self.get(side)
        if position is None:
            raise ValueError(f"No {side} position to close")

        self.set(side, None)
        return ClosedTrade(capital_return=position.capital_return(exit_price))
