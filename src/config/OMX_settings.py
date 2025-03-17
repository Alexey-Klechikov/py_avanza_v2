from dataclasses import dataclass, field
from datetime import time

from config.base_settings import BaseSettings


@dataclass
class TradeStrategies(BaseSettings):
    NAME: str = "OMX"
    ACCOUNT_ID: str = "754762"

    AVA: str = "19002"
    YAHOO: str = "^OMX"

    TRADING_DATA: str = "avanza"

    MULTIPLIER: int = 20

    TRADING_START: time = time(9, 45)
    TRADING_END: time = time(16, 58)

    BUDGET: float = 0.95

    TRADING_STRATEGY_MIN_EFFICIENCY: float = 0.6
    TRADING_STRATEGY_COUNT_MAX: int = 20
    TRADING_STRATEGY_INDICATORS: int = 7
    TRADING_TAKE_PROFIT: float = 0.09
    TRADING_STOP_LOSS: float = 0.05
    TRADING_STOP_LOSS_CONFIRMATION_COUNT_MIN: int = 4

    INDICATORS: dict = field(
        default_factory=lambda: {
            "Trend": {
                "ADX": {"length": 11, "lensig": 14, "mamode": "hma"},
                "TII": {"length_sma": 14, "length_signal": 8},
                "PSAR": {"acceleration": 0.02, "maximum": 0.2},
                "CHOP": {"length": 6, "length_atr": 14, "scalar": 55.0},
            },
            "Overlap": {
                "LINREG": {"length": 12, "limit": 0.32},
                "SLOPE": {"length": 18, "limit": 0.1},
                "SUPERTREND": {"length": 7, "multiplier": 3.0},
            },
            "Momentum": {
                "MACD_DEMA": {"length_fast": 16, "length_slow": 18},
                "STC": {"tclength": 10, "fast": 15, "slow": 31, "factor": 0.63},
                "CCI": {"length": 12, "c": 0.015},
                "RVGI": {"length": 24, "length_swma": 4, "length_divergence": 18},
                "STOCH": {"k": 14, "d": 3, "smooth_k": 2, "mamode": "rma"},
            },
            "Cycles": {
                "EBSW": {"length": 40, "bars": 18},
            },
            "Volatility": {
                "STARC": {"length_sma": 10, "length_atr": 14, "multiplier_atr": 2.2},
                "MASSI": {"fast": 6, "slow": 8, "threshold": 8},
                "BBANDS": {"length": 10, "std": 2.4},
                "ACCBANDS": {"length": 12, "c": 1, "mamode": "zlma"},
            },
            "Volume": {
                "PVT": {"drift": 14, "length_sma": 22, "length_divergence": 24},
                "ADOSC": {"fast": 6, "slow": 10, "length_divergence": 28},
                "CMF": {"length": 24, "length_divergence": 24},
                "KVO": {"fast": 14, "slow": 30, "signal": 14, "mamode": "rma", "length_divergence": 28},
            },
        },
    )
