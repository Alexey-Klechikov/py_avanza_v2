from dataclasses import dataclass, field
from datetime import time

from config.settings_base import BaseNASDAQ, BaseOMX, BaseTrade


@dataclass
class TradeOMX(BaseOMX, BaseTrade):
    TRADING_START: time = time(9, 45)
    TRADING_END: time = time(17, 0)
    TRADING_DATA: str = "avanza"

    BUDGET_MINIMUM: int = 2500
    BUDGET_PERCENT: float = 0.6

    TRADING_STRATEGY_INDICATORS: int = 7
    TRADING_TAKE_PROFIT: float = 0.11

    INDICATORS: dict = field(
        default_factory=lambda: {
            "Trend": {
                "ADX": {"length": 14, "lensig": 14, "mamode": "rma"},
                "TII": {"length_sma": 22, "length_signal": 3},
                "PSAR": {"acceleration": 0.02, "maximum": 0.2},
                "CHOP": {"length": 14, "length_atr": 2, "scalar": 80.0},
            },
            "Overlap": {
                "LINREG": {"length": 12, "limit": 0.32},
                "SUPERTREND": {"length": 7, "multiplier": 3.0},
            },
            "Momentum": {
                "MACD_DEMA": {"length_fast": 10, "length_slow": 20},
                "STC": {"tclength": 14, "fast": 23, "slow": 45, "factor": 0.55},
                "CCI": {"length": 14, "c": 0.015},
                "RVGI": {"length": 14, "length_swma": 4},
                "STOCH": {"k": 10, "d": 3, "smooth_k": 2, "mamode": "dema"},
            },
            "Cycles": {
                "EBSW": {"length": 40, "bars": 14},
            },
            "Volatility": {
                "STARC": {"length_sma": 10, "length_atr": 15, "multiplier_atr": 2.0},
                "MASSI": {"fast": 9, "slow": 25},
                "BBANDS": {"length": 22, "std": 2.0},
                "ACCBANDS": {"length": 14, "c": 1, "mamode": "dema"},
            },
            "Volume": {
                "PVT": {"drift": 12, "length_sma": 30},
                "ADOSC": {"fast": 6, "slow": 14},
                "CMF": {"length": 24},
                "KVO": {"fast": 11, "slow": 35, "signal": 18, "mamode": "ema"},
            },
        },
    )


@dataclass
class TradeNASDAQ(BaseNASDAQ, BaseTrade):
    TRADING_START: time = time(17, 0)
    TRADING_END: time = time(21, 50)
    TRADING_DATA: str = "yahoo"

    BUDGET_MINIMUM: int = 1500
    BUDGET_PERCENT: float = 0.4

    TRADING_STRATEGY_INDICATORS: int = 7
    TRADING_TAKE_PROFIT: float = 0.12

    INDICATORS: dict = field(
        default_factory=lambda: {
            "Trend": {
                "ADX": {"length": 10, "lensig": 16, "mamode": "rma"},
                "TII": {"length_sma": 12, "length_signal": 5},
                "PSAR": {"acceleration": 0.01, "maximum": 0.2},
                "CHOP": {"length": 14, "length_atr": 2, "scalar": 80.0},
            },
            "Overlap": {
                "LINREG": {"length": 8, "limit": 0.3},
                "SUPERTREND": {"length": 7, "multiplier": 3.0},
            },
            "Momentum": {
                "MACD_DEMA": {"length_fast": 10, "length_slow": 20},
                "STC": {"tclength": 10, "fast": 23, "slow": 45, "factor": 0.55},
                "CCI": {"length": 16, "c": 0.02},
                "RVGI": {"length": 14, "length_swma": 4},
                "STOCH": {"k": 10, "d": 3, "smooth_k": 2, "mamode": "dema"},
            },
            "Cycles": {
                "EBSW": {"length": 40, "bars": 16},
            },
            "Volatility": {
                "STARC": {"length_sma": 10, "length_atr": 15, "multiplier_atr": 2.0},
                "MASSI": {"fast": 9, "slow": 25},
                "BBANDS": {"length": 16, "std": 2.4},
                "ACCBANDS": {"length": 14, "c": 1, "mamode": "dema"},
            },
            "Volume": {
                "PVT": {"drift": 12, "length_sma": 30},
                "ADOSC": {"fast": 6, "slow": 14},
                "CMF": {"length": 24},
                "KVO": {"fast": 11, "slow": 35, "signal": 18, "mamode": "ema"},
            },
        },
    )
