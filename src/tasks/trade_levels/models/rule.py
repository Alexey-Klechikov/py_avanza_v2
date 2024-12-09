from datetime import datetime

from pydantic import BaseModel, Field


class Deal(BaseModel):
    buy_price: float = Field(default=0.0)
    buy_time: datetime = Field(default_factory=datetime.now)
    sell_price: float = Field(default=0.0)
    sell_time: datetime = Field(default_factory=datetime.now)

    profit: float = Field(default=0.0)

    def __str__(self):
        return (
            f"Buy price: {self.buy_price} [at {self.buy_time}], "
            + f"Sell price: {self.sell_price} [at {self.sell_time}], "
            + f"Profit: {round(self.profit, 2)}"
        )
