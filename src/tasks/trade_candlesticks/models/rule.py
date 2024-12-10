from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from apis.avanza.trade.models import Direction


class Deal(BaseModel):
    buy_price: float = Field(default=0.0)
    buy_time: datetime = Field(default_factory=datetime.now)
    sell_price: float = Field(default=0.0)
    profit: float = Field(default=0.0)
    duration: int = Field(default=0)


class CandlestickPatternRule(BaseModel):
    column: str
    direction: Direction

    take_profit: float | int = Field(default=0.0)
    stop_loss: float | int = Field(default=0.0)
    deals: list[Deal] = Field(default_factory=list)

    average_duration: int = Field(default=0)
    profit: float = Field(default=0.0)
    efficiency: float = Field(default=0.0)
    count_deals: int = Field(default=0)

    def __str__(self) -> str:
        return (
            f"{self.column} & {self.direction} ---> "
            + f"profit {self.profit}, eff. {self.efficiency}, durat. {self.average_duration}, "
            + f"deals {self.count_deals}, TP {self.take_profit}, SL {self.stop_loss}"
        )

    def aggregate_values_from_deals(self) -> None:
        if not self.deals:
            return

        self.average_duration = round(sum([i.duration for i in list(self.deals)]) / len(self.deals))
        self.profit = round(sum([i.profit for i in list(self.deals)]), 2)
        self.efficiency = round(len([i for i in list(self.deals) if i.profit > 0]) / len(self.deals), 2)
        self.count_deals = len(self.deals)

    def dump_dict(self, reference_price: int | None = None) -> dict[str, Any]:
        return {
            "column": self.column,
            "direction": self.direction.value,
            "profit": round(self.profit, 2),
            "efficiency": round(self.efficiency, 2),
            "average_duration": int(self.average_duration),
            "take_profit": round((self.take_profit / reference_price * 20) if reference_price else self.take_profit, 2),
            "stop_loss": round((self.stop_loss / reference_price * 20) if reference_price else self.stop_loss, 2),
            "count_deals": self.count_deals,
        }
