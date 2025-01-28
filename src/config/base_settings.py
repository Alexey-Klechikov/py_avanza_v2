from dataclasses import dataclass


@dataclass
class BaseSettings:
    ACCOUNT_ID: str = "5554179"
    TRADING_DATA: str = "avanza"
    RESOLUTION = "2m"
