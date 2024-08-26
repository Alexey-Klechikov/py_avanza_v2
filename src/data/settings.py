from dataclasses import dataclass


@dataclass
class OMX:
    NAME: str = "OMX (Sweden)"

    AVA: str = "19002"
    YAHOO: str = "^OMX"
    INVESTING: str = "25685"


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
BACKTEST_LOG_INDIVIDUAL_TRADES = False
