from dataclasses import dataclass


@dataclass
class BaseTrade:
    ACCOUNT_ID: str = "5554179"


@dataclass
class BaseHold:
    ACCOUNT_ID: str = "9568450"


@dataclass
class BaseOMX:
    NAME: str = "OMX"

    AVA: str = "19002"
    YAHOO: str = "^OMX"
    INVESTING: str = "25685"

    MULTIPLIER: int = 20
    RESOLUTION = "2m"

    REF_PRICE: float = 2600
