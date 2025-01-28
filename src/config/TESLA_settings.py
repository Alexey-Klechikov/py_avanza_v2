from dataclasses import dataclass
from datetime import time

from config.base_settings import BaseSettings


@dataclass
class TradeStrategies(BaseSettings):
    NAME: str = "TESLA"

    AVA: str = "238449"
    YAHOO: str = "TSLA"

    MULTIPLIER: int = 10

    TRADING_START: time = time(17, 15)
    TRADING_END: time = time(21, 45)
