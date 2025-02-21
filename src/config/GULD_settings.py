from dataclasses import dataclass, field
from datetime import time

from config.base_settings import BaseSettings


@dataclass
class TradeStrategies(BaseSettings):
    NAME: str = "GULD"
    ACCOUNT_ID: str = "5554179"

    AVA: str = "18986"
    YAHOO: str = "GC=F"

    TRADING_DATA: str = "yahoo"

    MULTIPLIER: int = 20

    TRADING_START: time = time(9, 1)
    TRADING_END: time = time(21, 45)

    BUDGET: float = 0.95

    TRADING_STRATEGY_INDICATORS: int = 7
    TRADING_TAKE_PROFIT: float = 0.08
    TRADING_STOP_LOSS: float = 0.04

    INDICATORS: dict = field(
        default_factory=lambda: {
            "Trend": {
                "ADX": {"length": 7, "lensig": 14, "mamode": "hma"},
                "TII": {"length_sma": 28, "length_signal": 14},
                "PSAR": {"acceleration": 0.02, "maximum": 0.25},
                "CHOP": {"length": 18, "length_atr": 8, "scalar": 74.0},
            },
            "Overlap": {
                "LINREG": {"length": 8, "limit": 0.38},
                "SLOPE": {"length": 14, "limit": 0.1},
                "SUPERTREND": {"length": 7, "multiplier": 4.0},
            },
            "Momentum": {
                "MACD_DEMA": {"length_fast": 10, "length_slow": 26},
                "STC": {"tclength": 14, "fast": 22, "slow": 43, "factor": 0.57},
                "CCI": {"length": 16, "c": 0.015},
                "RVGI": {"length": 18, "length_swma": 5, "length_divergence": 22},
                "STOCH": {"k": 16, "d": 2, "smooth_k": 1, "mamode": "rma"},
            },
            "Cycles": {
                "EBSW": {"length": 42, "bars": 14},
            },
            "Volatility": {
                "STARC": {"length_sma": 22, "length_atr": 24, "multiplier_atr": 2.0},
                "MASSI": {"fast": 8, "slow": 20, "threshold": 22},
                "BBANDS": {"length": 11, "std": 2.6},
                "ACCBANDS": {"length": 12, "c": 1, "mamode": "linreg"},
            },
            "Volume": {
                "PVT": {"drift": 14, "length_sma": 22, "length_divergence": 22},
                "ADOSC": {"fast": 6, "slow": 12, "length_divergence": 34},
                "CMF": {"length": 24, "length_divergence": 16},
                "KVO": {"fast": 8, "slow": 32, "signal": 10, "mamode": "rma", "length_divergence": 22},
            },
        },
    )
