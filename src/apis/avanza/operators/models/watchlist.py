from datetime import date

from pydantic import BaseModel, Field


class Orderbook(BaseModel):
    id: str
    type: str
    name: str
    spread: float | None
    buy: float | None
    sell: float | None
    leverage: float
    start_date: date


class ValidInstruments(BaseModel):
    BULL: list[Orderbook] = Field(default_factory=list)
    BEAR: list[Orderbook] = Field(default_factory=list)

    def get(self, direction: str) -> list[Orderbook]:
        if direction == "BULL":
            return self.BULL
        elif direction == "BEAR":
            return self.BEAR
        else:
            raise ValueError(f"Unknown direction: {direction}")

    def set(self, direction: str, value: list[Orderbook]) -> None:
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
    BULL: Orderbook | None = Field(default=None)
    BEAR: Orderbook | None = Field(default=None)

    def get(self, direction: str) -> Orderbook | None:
        if direction == "BULL":
            return self.BULL
        elif direction == "BEAR":
            return self.BEAR
        else:
            raise ValueError(f"Unknown direction: {direction}")

    def set(self, direction: str, value: Orderbook | None) -> None:
        if direction == "BULL":
            self.BULL = value
        elif direction == "BEAR":
            self.BEAR = value
        else:
            raise ValueError(f"Unknown direction: {direction}")
