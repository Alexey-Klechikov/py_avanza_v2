from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class Orderbook(BaseModel):
    id: str
    type: str
    name: str
    spread: Optional[float]
    buy: Optional[float]
    sell: Optional[float]
    leverage: float
    start_date: date


class ValidInstruments(BaseModel):
    BULL: List[Orderbook] = Field(default_factory=list)
    BEAR: List[Orderbook] = Field(default_factory=list)

    def get(self, direction: str) -> List[Orderbook]:
        if direction == "BULL":
            return self.BULL
        elif direction == "BEAR":
            return self.BEAR
        else:
            raise ValueError(f"Unknown direction: {direction}")

    def set(self, direction: str, value: List[Orderbook]) -> None:
        if direction == "BULL":
            self.BULL = value
        elif direction == "BEAR":
            self.BEAR = value
        else:
            raise ValueError(f"Unknown direction: {direction}")

    def append(self, direction: str, value: Orderbook) -> None:
        if direction == "BULL":
            self.BULL.append(value)
        elif direction == "BEAR":
            self.BEAR.append(value)
        else:
            raise ValueError(f"Unknown direction: {direction}")


class PreferredInstrument(BaseModel):
    BULL: Optional[Orderbook] = Field(default=None)
    BEAR: Optional[Orderbook] = Field(default=None)

    def get(self, direction: str) -> Optional[Orderbook]:
        if direction == "BULL":
            return self.BULL
        elif direction == "BEAR":
            return self.BEAR
        else:
            raise ValueError(f"Unknown direction: {direction}")

    def set(self, direction: str, value: Optional[Orderbook]) -> None:
        if direction == "BULL":
            self.BULL = value
        elif direction == "BEAR":
            self.BEAR = value
        else:
            raise ValueError(f"Unknown direction: {direction}")
