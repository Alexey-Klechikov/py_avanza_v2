from dataclasses import dataclass, field
from datetime import time


@dataclass(frozen=True)
class SettingsWatchlist:
    INSTRUMENT_DIRECTIONS = {"Kort": "BEAR", "Lång": "BULL"}

    TRADING_PERSPECTIVE_PREFIX = "DT"
    WATCHLIST_NAME_PARTS = 4

    LEVERAGE_LOWER_MULTIPLIER = 0.85
    LEVERAGE_UPPER_MULTIPLIER = 1.15

    MIN_SPREAD_PERCENT = 0.1
    MIN_PRICE = 1
    MAX_PRICE = 300

    SEARCH_WARRANT_PREFIX = {"BULL": "L", "BEAR": "S"}


@dataclass(frozen=True)
class StopLoss:
    # Stop and take-profit levels are per signal source (ExitLevels): a move of the instrument at the nominal
    # MULTIPLIER, set on the underlying at level / MULTIPLIER from entry; the live take-profit order on the instrument
    # scales that underlying move by the instrument's actual leverage.
    # The stop loss is confirmed once CONFIRMATION_COUNT + 1 consecutive completed bars close beyond the level.
    CONFIRMATION_COUNT: int = 3


@dataclass(frozen=True)
class Pullback:
    # Once the peak profit passes the source's ExitLevels.pullback_trigger, a pullback is confirmed after
    # CONFIRMATION_COUNT + 1 consecutive closes that lost more than VALUE of that peak (0.4: a 10% peak falling below
    # 6%) or turned the profit negative.
    VALUE: float = 0.0
    CONFIRMATION_COUNT: int = 2


@dataclass(frozen=True)
class Time:
    # The time range during which the trading is active, in Stockholm time (host clock and cached bars): the US
    # session 15:30-22:00 less its first 45 and last 15 minutes. In the weeks the US and European clock changes
    # differ, the session runs 14:30-21:00 and the NYSE close (services/calendar) ends the day instead: the live loop
    # stops at the close minus 11 minutes (20:49), while the backtest holds to the session's last bar (21:00), so
    # those ~4 weeks a year replay up to ~11 minutes longer than live (also on early-close days).
    START: time = time(16, 15)
    END: time = time(21, 45)


@dataclass(frozen=True)
class WeightedScore:
    # Every indicator on every resolution votes: "dir" is +1 on its LONG signal, -1 on SHORT, 0 otherwise. Intraday
    # RESOLUTIONS are built from the 2m cache (a coarse bar counts from the 2m bar that completes it); USE_DAILY adds
    # the 1d cache's indicators as of the previous session.
    # A weight per vote is fitted (L1: useless votes get weight 0) to the underlying move over the next
    # HORIZON_BARS 2m bars (exit fill, capped at TIME.END; clipped at TARGET_CLIP_SD standard deviations, 0: off), on
    # the TRAIN_DAYS calendar days before training (0: all cached history). The score is the weighted sum;
    # BULL above the training ENTRY_QUANTILE of |score - median|, BEAR below its negative. A position is held exactly
    # HORIZON_BARS completed bars, the move the score predicts, then sold at the next open (or at TIME.END); signals
    # are ignored meanwhile. TAKE_PROFIT / STOP_LOSS / PULLBACK_TRIGGER of None turn those exits off, as calibrated.
    # The model lives in config/<NAME>_weighted_model.json: task_end_of_week refits it, and its weights can be edited
    # by hand between refits.
    # These defaults were calibrated on OMX (2024-11..2026-11). TSLA walk-forward 2026-11-19 with them and volume
    # votes (850 out-of-sample sessions 2023-07..2026-11, refit every 5): correlation +0.037 (weekly t 3.2, every year
    # positive), top 5% of scores +23 bp gross per trade (t 3.6, longs and shorts both beat the drift); but TSLA was
    # the best of 5 stocks on overlapping data and 2024 was near flat, so it needs a forward paper test.
    # TSLA volume history is rebuilt (IEX scaled to Yahoo, then to Avanza's intraday scale): see README "Data".
    # Single weights shuffle between correlated votes from refit to refit, so read the score, not one weight.
    RESOLUTIONS: tuple[str, ...] = ("30min", "60min")
    USE_DAILY: bool = True
    HORIZON_BARS: int = 60
    TARGET_CLIP_SD: float = 3.0
    TRAIN_DAYS: int = 365
    # L1 strengths tried (on standardized votes, target in bp); the one with the best correlation on the last
    # VALIDATION_SHARE of the training data (still before the model's use) is refitted on all of it
    ALPHAS: tuple[float, ...] = (0.1, 0.3, 1.0, 3.0)
    VALIDATION_SHARE: float = 0.2
    ENTRY_QUANTILE: float = 0.95
    TAKE_PROFIT: float | None = None
    STOP_LOSS: float | None = None
    PULLBACK_TRIGGER: float | None = None
    # Calendar days of 2m history the live loop and the paper replay compute votes on
    WARMUP_DAYS: int = 60


@dataclass(frozen=True)
class TradeSettings:
    NAME: str = "TSLA"
    ACCOUNT_ID: str = "754762"

    DATA_SOURCE: str = "avanza"
    RESOLUTION: str = "2m"
    MULTIPLIER: int = 10
    SPREAD_MAX: float = 0.004  # 0.4%: watchlist ceiling for an instrument's spread
    # The only trading cost: the spread, paid once per trade on the sale (the instrument is sold this fraction below
    # its actual price; the buy fills at the actual price). Charged on every backtest trade.
    SPREAD_DEFAULT: float = 0.002

    AVA: str = "238449"
    YAHOO: str = "TSLA"

    STOP_LOSS: StopLoss = field(default_factory=StopLoss)
    PULLBACK: Pullback = field(default_factory=Pullback)
    TIME: Time = field(default_factory=Time)
    WEIGHTED_SCORE: WeightedScore = field(default_factory=WeightedScore)
    # True: task_trade places orders on the weighted score's signals. False: its signals are only logged as [PAPER].
    # Either way task_end_of_day replays the session into logs/paper_trades_<NAME>_weighted.json.
    # Off until TSLA's forward paper journal confirms the edge.
    LIVE_ORDERS: bool = False

    BUDGET: float = 1.0

    # Indicators that vote in the weighted score: each needs a LONG/SHORT direction signal
    INDICATORS: dict[str, dict[str, dict[str, int | float | str]]] = field(
        default_factory=lambda: {
            "Trend": {
                "ADX": {"length": 11, "lensig": 14, "mamode": "hma"},
                "TII": {"length_sma": 16, "length_signal": 4},
                "PSAR": {"acceleration": 0.01, "maximum": 0.2},
            },
            "Overlap": {
                "LINREG": {"length": 14, "limit": 0.34},
                "SLOPE": {"length": 18, "limit": 0.1},
                "SUPERTREND": {"length": 15, "multiplier": 7.0},
            },
            "Momentum": {
                "MACD_DEMA": {"length_fast": 22, "length_slow": 14},
                "STC": {"tclength": 10, "fast": 23, "slow": 50, "factor": 0.5},
                "CCI": {"length": 12, "c": 0.015},
                "RVGI": {"length": 18, "length_swma": 3, "length_divergence": 22},
                "STOCH": {"k": 14, "d": 3, "smooth_k": 2, "mamode": "rma"},
            },
            "Cycles": {"EBSW": {"length": 40, "bars": 18}},
            "Volatility": {
                "STARC": {"length_ma": 10, "length_atr": 8, "multiplier_atr": 2.4},
                "BBANDS": {"length": 16, "std": 2.4},
                "ACCBANDS": {"length": 14, "c": 2, "mamode": "vidya"},
            },
            "Volume": {
                "PVT": {"drift": 14, "length_sma": 22, "length_divergence": 24},
                "ADOSC": {"fast": 6, "slow": 10, "length_divergence": 28},
                "CMF": {"length": 28, "length_divergence": 32},
                "KVO": {"fast": 22, "slow": 55, "signal": 10, "mamode": "rma", "length_divergence": 30},
            },
        },
    )
