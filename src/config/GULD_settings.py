from dataclasses import dataclass, field
from datetime import time

from config.base_settings import BaseSettings


@dataclass
class TradeStrategies(BaseSettings):
    NAME: str = "GULD"

    AVA: str = "18986"
    YAHOO: str = "GC=F"

    MULTIPLIER: int = 20

    TRADING_START: time = time(9, 45)
    TRADING_END: time = time(16, 58)

    BUDGET: float = 0.7

    TRADING_STRATEGY_INDICATORS: int = 7
    TRADING_TAKE_PROFIT: float = 0.075
    TRADING_STOP_LOSS: float = 0.05

    INDICATORS: dict = field(
        default_factory=lambda: {
            "Trend": {
                "ADX": {"length": 11, "lensig": 14, "mamode": "hma"},
                "TII": {"length_sma": 32, "length_signal": 5},
                "PSAR": {"acceleration": 0.02, "maximum": 0.2},
                "CHOP": {"length": 18, "length_atr": 11, "scalar": 80.0},
            },
            "Overlap": {
                "LINREG": {"length": 12, "limit": 0.32},
                "SLOPE": {"length": 24, "limit": 0},
                "SUPERTREND": {"length": 7, "multiplier": 3.0},
            },
            "Momentum": {
                "MACD_DEMA": {"length_fast": 16, "length_slow": 18},
                "STC": {"tclength": 14, "fast": 25, "slow": 45, "factor": 0.55},
                "CCI": {"length": 12, "c": 0.015},
                "RVGI": {"length": 20, "length_swma": 4, "length_divergence": 20},
                "STOCH": {"k": 14, "d": 3, "smooth_k": 2, "mamode": "rma"},
            },
            "Cycles": {
                "EBSW": {"length": 40, "bars": 14},
            },
            "Volatility": {
                "STARC": {"length_sma": 18, "length_atr": 20, "multiplier_atr": 2.4},
                "MASSI": {"fast": 5, "slow": 23, "threshold": 23},
                "BBANDS": {"length": 13, "std": 2.7},
                "ACCBANDS": {"length": 12, "c": 1, "mamode": "zlma"},
            },
            "Volume": {
                "PVT": {"drift": 12, "length_sma": 30, "length_divergence": 24},
                "ADOSC": {"fast": 6, "slow": 14, "length_divergence": 28},
                "CMF": {"length": 24, "length_divergence": 24},
                "KVO": {"fast": 14, "slow": 30, "signal": 14, "mamode": "rma", "length_divergence": 28},
            },
        },
    )
