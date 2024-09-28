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
