from dataclasses import dataclass
from datetime import time


@dataclass
class TRADING:
    MULTIPLIER: int = 20
    RESOLUTION = "2m"


@dataclass
class OMX(TRADING):
    NAME: str = "OMX"
    DIR: str = "OMX"

    AVA: str = "19002"
    YAHOO: str = "^OMX"
    INVESTING: str = "25685"

    TRADING_START: time = time(9, 45)
    TRADING_END: time = time(17, 0)
    TRADING_DATA: str = "avanza"

    BUDGET_MINIMUM: int = 2500
    BUDGET_PERCENT: float = 0.6

    TRADING_STRATEGY_INDICATORS: int = 7


@dataclass
class NASDAQ(TRADING):
    NAME: str = "NASDAQ"
    DIR: str = "NDX"

    AVA: str = "155541"
    YAHOO: str = "^NDX"
    INVESTING: str = "20"

    TRADING_START: time = time(17, 0)
    TRADING_END: time = time(21, 50)
    TRADING_DATA: str = "yahoo"

    BUDGET_MINIMUM = 1500
    BUDGET_PERCENT: float = 0.3

    TRADING_STRATEGY_INDICATORS: int = 5


@dataclass
class SETTINGS:
    OMX = OMX()
    NASDAQ = NASDAQ()


@dataclass
class AVANZA_ACCOUNT:
    USERNAME: str = "ava_elbe"
    ACCOUNT_ID: str = "5554179"


DATA_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]
