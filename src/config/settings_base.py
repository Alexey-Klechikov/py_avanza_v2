from dataclasses import dataclass


@dataclass
class BaseTrade:
    ACCOUNT_ID: str = "5554179"

    MULTIPLIER: int = 20
    RESOLUTION = "2m"


@dataclass
class BaseHold:
    ACCOUNT_ID: str = "9568450"

    MULTIPLIER: int = 20


@dataclass
class BaseOMX:
    NAME: str = "OMX"
    FILE_PREFIX: str = "OMX"

    AVA: str = "19002"
    YAHOO: str = "^OMX"
    INVESTING: str = "25685"


@dataclass
class BaseNASDAQ:
    NAME: str = "NASDAQ"
    FILE_PREFIX: str = "NDX"

    AVA: str = "155541"
    YAHOO: str = "^NDX"
    INVESTING: str = "20"
