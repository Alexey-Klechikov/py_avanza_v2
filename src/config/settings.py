import platform
from dataclasses import dataclass, field
from datetime import time


@dataclass
class Strategy:
    MIN_EFFICIENCY: float = 0.6
    COUNT_MAX: int = 30
    INDICATORS: int = 7


@dataclass
class TakeProfit:
    # The percentage from the buy price that the price must rise to trigger a take profit
    # Example: 0.09 means that if the buy price is 100 and the price rises to 109, a take profit is triggered
    VALUE: float = 0.09


@dataclass
class StopLoss:
    # The percentage from the buy price that the price must fall to trigger a stop loss
    # Example: 0.06 means that if the buy price is 100 and the price falls to 94, a stop loss is triggered
    # The stop loss is confirmed if the price falls below the buy price by this percentage for a certain number of times
    VALUE: float = 0.06
    CONFIRMATION_COUNT: int = 4


@dataclass
class Pullback:
    # The percentage of the maximum profit that must be lost before a pullback is confirmed
    # Example: 0.4 means that if the maximum profit is 10% and the current profit is 6%, a pullback is confirmed
    # The pullback is confirmed if the price falls below the buy price by this percentage for a certain number of times
    VALUE: float = 0.4
    CONFIRMATION_COUNT: int = 2
    TRIGGER_PROFIT: float = 0.02


@dataclass
class Time:
    # The time range during which the trading is active
    START: time = time(9, 45)
    END: time = time(17, 15)


@dataclass
class TradeStrategies:
    DRY_RUN: bool = platform.system() == "Darwin"

    NAME: str = "OMX"
    ACCOUNT_ID: str = "754762"

    DATA_SOURCE: str = "avanza"
    RESOLUTION: str = "2m"
    MULTIPLIER: int = 20

    AVA: str = "19002"
    YAHOO: str = "^OMX"

    STRATEGY: Strategy = field(default_factory=Strategy)
    TAKE_PROFIT: TakeProfit = field(default_factory=TakeProfit)
    STOP_LOSS: StopLoss = field(default_factory=StopLoss)
    PULLBACK: Pullback = field(default_factory=Pullback)
    TIME: Time = field(default_factory=Time)

    BUDGET: float = 1.0

    INDICATORS: dict = field(
        default_factory=lambda: {
            "Trend": {
                "ADX": {"length": 11, "lensig": 14, "mamode": "hma"},
                "TII": {"length_sma": 14, "length_signal": 8},
                "PSAR": {"acceleration": 0.01, "maximum": 0.2},
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
                # "CCI": {"length": 12, "c": 0.015},
                "RVGI": {"length": 18, "length_swma": 3, "length_divergence": 22},
                "STOCH": {"k": 14, "d": 3, "smooth_k": 2, "mamode": "rma"},
            },
            "Cycles": {
                "EBSW": {"length": 40, "bars": 18},
            },
            "Volatility": {
                "STARC": {"length_ma": 12, "length_atr": 14, "multiplier_atr": 1.8, "mamode": "wma"},
                # "MASSI": {"fast": 9, "slow": 23, "threshold": 26.5},
                "BBANDS": {"length": 10, "std": 2.4},
                "ACCBANDS": {"length": 12, "c": 1, "mamode": "zlma"},
            },
            "Volume": {
                "PVT": {"drift": 14, "length_sma": 22, "length_divergence": 24},
                "ADOSC": {"fast": 6, "slow": 10, "length_divergence": 28},
                # "CMF": {"length": 28, "length_divergence": 32},
                # "KVO": {"fast": 22, "slow": 55, "signal": 10, "mamode": "rma", "length_divergence": 30},
            },
        },
    )
