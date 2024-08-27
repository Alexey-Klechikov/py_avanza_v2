from dataclasses import dataclass
from datetime import time


@dataclass
class OMX:
    NAME: str = "OMX (Sweden)"
    DIR: str = "OMX"

    AVA: str = "19002"
    YAHOO: str = "^OMX"
    INVESTING: str = "25685"

    TRADING_START: time = time(9, 45)
    TRADING_END: time = time(17, 0)


@dataclass
class NASDAQ:
    NAME: str = "NASDAQ (USA)"
    DIR: str = "NDX"

    AVA: str = "155541"
    YAHOO: str = "^NDX"
    INVESTING: str = "20"

    TRADING_START: time = time(17, 0)
    TRADING_END: time = time(21, 50)


@dataclass
class AVANZA_ACCOUNT:
    USERNAME: str = "ava_elbe"
    ACCOUNT_ID: str = "5554179"


@dataclass
class TRADING:
    MULTIPLIER: int = 20
    RESOLUTION = "2m"
    MINIMUM_BUDGET = 2000


DATA_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]
