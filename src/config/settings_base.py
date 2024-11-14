from dataclasses import dataclass


@dataclass
class BaseTradeStrategies:
    ACCOUNT_ID: str = "5554179"


@dataclass
class BaseHoldStatistics:
    ACCOUNT_ID: str = "7143979"


@dataclass
class BaseHoldCorrelation:
    ACCOUNT_ID: str = ""  # -> BaseTradeCandlesticks


@dataclass
class BaseTradeCandlesticks:
    ACCOUNT_ID: str = "7144096"


@dataclass
class BaseOMX:
    NAME: str = "OMX"

    AVA: str = "19002"
    YAHOO: str = "^OMX"
    INVESTING: str = "25685"

    MULTIPLIER: int = 20
    RESOLUTION = "2m"

    REF_PRICE: float = 2600
