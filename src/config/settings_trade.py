from dataclasses import dataclass, field
from datetime import time

from config.settings_base import BaseOMX, BaseTradeCandlesticks, BaseTradeStrategies


@dataclass
class TradeStrategies(BaseOMX, BaseTradeStrategies):
    TRADING_START: time = time(9, 45)
    TRADING_END: time = time(16, 58)
    TRADING_DATA: str = "avanza"

    BUDGET: int = 2500

    TRADING_STRATEGY_INDICATORS: int = 7
    TRADING_TAKE_PROFIT: float = 0.08
    TRADING_STOP_LOSS: float = 0.06

    INDICATORS: dict = field(
        default_factory=lambda: {
            "Trend": {
                "ADX": {"length": 10, "lensig": 12, "mamode": "rma"},
                "TII": {"length_sma": 22, "length_signal": 3},
                "PSAR": {"acceleration": 0.02, "maximum": 0.2},
                "CHOP": {"length": 14, "length_atr": 2, "scalar": 80.0},
            },
            "Overlap": {
                "LINREG": {"length": 12, "limit": 0.32},
                "SLOPE": {"length": 24, "limit": 0},
                "SUPERTREND": {"length": 7, "multiplier": 3.0},
            },
            "Momentum": {
                "MACD_DEMA": {"length_fast": 16, "length_slow": 18},
                "STC": {"tclength": 14, "fast": 23, "slow": 45, "factor": 0.55},
                "CCI": {"length": 14, "c": 0.015},
                "RVGI": {"length": 14, "length_swma": 4, "length_divergence": 14},
                "STOCH": {"k": 10, "d": 3, "smooth_k": 2, "mamode": "dema"},
            },
            "Cycles": {
                "EBSW": {"length": 40, "bars": 14},
            },
            "Volatility": {
                "STARC": {"length_sma": 16, "length_atr": 14, "multiplier_atr": 2.0},
                "MASSI": {"fast": 9, "slow": 25},
                "BBANDS": {"length": 12, "std": 2.0},
                "ACCBANDS": {"length": 14, "c": 1, "mamode": "dema"},
            },
            "Volume": {
                "PVT": {"drift": 12, "length_sma": 30, "length_divergence": 24},
                "ADOSC": {"fast": 6, "slow": 14, "length_divergence": 28},
                "CMF": {"length": 24, "length_divergence": 24},
                "KVO": {"fast": 11, "slow": 35, "signal": 18, "mamode": "ema", "length_divergence": 30},
            },
        },
    )


@dataclass
class TradeCandlesticks(BaseOMX, BaseTradeCandlesticks):
    TRADING_START: time = time(9, 10)
    TRADING_END: time = time(17, 10)
    TRADING_DATA: str = "avanza"

    BUDGET: float = 2000
