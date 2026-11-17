import platform
from dataclasses import dataclass, field
from datetime import time


@dataclass(frozen=True)
class SettingsWatchlist:
    INSTRUMENT_DIRECTIONS = {"Kort": "BEAR", "Lång": "BULL"}

    TRADING_PERSPECTIVE_PREFIX = "DT"
    WATCHLIST_NAME_PARTS = 4

    # Leverage tolerance constants
    LEVERAGE_LOWER_MULTIPLIER = 0.85
    LEVERAGE_UPPER_MULTIPLIER = 1.15

    # Price and spread constants
    MIN_SPREAD_PERCENT = 0.1
    MIN_PRICE = 1
    MAX_PRICE = 300

    # Search prefix constants
    SEARCH_WARRANT_PREFIX = {"BULL": "L", "BEAR": "S"}


@dataclass(frozen=True)
class Strategy:
    MIN_EFFICIENCY: float = 0.6
    COUNT_MAX: int = 200
    INDICATORS_START: int = 2
    INDICATORS: int = 7
    FALLBACK_COUNT: int = 5

    # Calibration windows: train on TRAIN_DAYS that end HOLDOUT_DAYS ago, final-test on the last HOLDOUT_DAYS
    TRAIN_DAYS: int = 90
    HOLDOUT_DAYS: int = 30
    # Fewer training trades than this cannot rank: a handful of lucky trades is not an edge
    MIN_TRADES_TRAIN: int = 15
    # Calibration stops (DataQualityError) when fewer of a window's days than this have complete candles;
    # partial-candle days are always dropped (services/storage/candle_quality.py)
    MIN_CLEAN_DAY_SHARE: float = 0.8

    # Daily selection (final test and end of day): expected capital return per trade, where each past trade's
    # weight halves every SCORE_HALF_LIFE_DAYS and SCORE_PRIOR_TRADES zero-return pseudo-trades shrink small samples.
    # Strategies at or below MIN_EDGE are dropped; none left means no trading that day.
    # Choose these with development.py run_selection_walk_forward (2026-11-17, 312 days, 3-indicator pool: best of
    # half-life 10-inf x prior 0-30 x min edge 0-0.2%, still -0.05% per traded day, sitting out 18% of days).
    SCORE_HALF_LIFE_DAYS: float = 20
    SCORE_PRIOR_TRADES: float = 30
    MIN_EDGE: float = 0.002

    # After a strategy triggers, lower-ranked strategies are ignored for this long (live loop and replay)
    TRIGGER_LOCK_MINUTES: int = 40


@dataclass(frozen=True)
class TakeProfit:
    # Take-profit move of the instrument at the nominal MULTIPLIER. Levels are set on the underlying at
    # VALUE / MULTIPLIER from entry (backtest and live alike); the live limit order on the instrument scales that
    # underlying move by the instrument's actual leverage.
    # Example: 0.045 with MULTIPLIER 10 means a take profit once the underlying moves 0.45% in the trade's favour
    VALUE: float = 0.045


@dataclass(frozen=True)
class StopLoss:
    # Stop-loss move of the instrument at the nominal MULTIPLIER, set on the underlying at VALUE / MULTIPLIER from
    # entry. On an instrument with higher actual leverage the instrument loss at the stop is proportionally larger.
    # Example: 0.03 with MULTIPLIER 10 means a stop once the underlying moves 0.3% against the trade
    # The stop loss is confirmed when CONFIRMATION_COUNT + 1 consecutive completed bars close beyond the level
    VALUE: float = 0.030
    CONFIRMATION_COUNT: int = 3


@dataclass(frozen=True)
class Pullback:
    # The percentage of the maximum profit that must be lost before a pullback is confirmed
    # Example: 0.4 means that if the maximum profit is 10% and the current profit is 6%, a pullback is confirmed
    # The pullback is confirmed if the price falls below the buy price by the percentage for a certain number of times
    VALUE: float = 0.0
    CONFIRMATION_COUNT: int = 2
    TRIGGER_PROFIT: float = TakeProfit.VALUE / 2


@dataclass(frozen=True)
class Time:
    # The time range during which the trading is active
    START: time = time(9, 45)
    END: time = time(17, 15)


@dataclass(frozen=True)
class TradeStrategies:
    DRY_RUN: bool = platform.system() == "Darwin"

    NAME: str = "OMX"
    ACCOUNT_ID: str = "754762"

    DATA_SOURCE: str = "avanza"
    RESOLUTION: str = "2m"
    MULTIPLIER: int = 10
    MAX_SPREAD: float = 0.004  # 0.4%: watchlist ceiling for an instrument's spread
    # Trading costs as fractions of the instrument price, charged on every backtest trade:
    # SPREAD is paid once per round trip (buy at the ask, sell at the bid); typical AVA mini futures quote ~0.10-0.12%.
    # COMMISSION_PER_ORDER is the courtage rate, charged on the buy and on the sell. AVA-branded products are
    # courtage-free on Avanza for orders above 1,000 SEK (the bot's minimum budget is 1,200 SEK); check your
    # courtage class and set it if you pay commission.
    SPREAD: float = 0.0012
    COMMISSION_PER_ORDER: float = 0.0

    AVA: str = "19002"
    YAHOO: str = "^OMX"

    STRATEGY: Strategy = field(default_factory=Strategy)
    TAKE_PROFIT: TakeProfit = field(default_factory=TakeProfit)
    STOP_LOSS: StopLoss = field(default_factory=StopLoss)
    PULLBACK: Pullback = field(default_factory=Pullback)
    TIME: Time = field(default_factory=Time)

    BUDGET: float = 1.0

    @property
    def ROUND_TRIP_COST(self) -> float:
        """Total cost of one trade (buy and sell) as a fraction of the instrument price."""
        return self.SPREAD + 2 * self.COMMISSION_PER_ORDER

    INDICATORS: dict = field(
        default_factory=lambda: {
            "Trend": {
                "ADX": {"length": 11, "lensig": 14, "mamode": "hma"},
                "TII": {"length_sma": 16, "length_signal": 4},
                "PSAR": {"acceleration": 0.01, "maximum": 0.2},
                "CHOP": {"length": 6, "length_atr": 6, "scalar": 51.0},
            },
            "Overlap": {
                "LINREG": {"length": 14, "limit": 0.34},
                "SLOPE": {"length": 18, "limit": 0.1},
                "SUPERTREND": {"length": 15, "multiplier": 7.0},
            },
            "Momentum": {
                "MACD_DEMA": {"length_fast": 22, "length_slow": 14},
                "STC": {"tclength": 10, "fast": 10, "slow": 20, "factor": 0.63},
                # "CCI": {"length": 12, "c": 0.015},
                "RVGI": {"length": 18, "length_swma": 3, "length_divergence": 22},
                "STOCH": {"k": 14, "d": 3, "smooth_k": 2, "mamode": "rma"},
            },
            "Cycles": {"EBSW": {"length": 40, "bars": 18}},
            "Volatility": {
                "STARC": {"length_ma": 10, "length_atr": 8, "multiplier_atr": 2.4},
                # "MASSI": {"fast": 9, "slow": 23, "threshold": 26.5},
                "BBANDS": {"length": 16, "std": 2.4},
                "ACCBANDS": {"length": 14, "c": 2, "mamode": "vidya"},
            },
            "Volume": {
                # "PVT": {"drift": 14, "length_sma": 22, "length_divergence": 24},
                # "ADOSC": {"fast": 6, "slow": 10, "length_divergence": 28},
                # "CMF": {"length": 28, "length_divergence": 32},
                # "KVO": {"fast": 22, "slow": 55, "signal": 10, "mamode": "rma", "length_divergence": 30}
            },
        },
    )
