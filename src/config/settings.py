from dataclasses import dataclass, field
from datetime import date, time


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
class StopLoss:
    # Stop and take-profit levels are per signal source (ExitLevels): a move of the instrument at the nominal
    # MULTIPLIER, set on the underlying at level / MULTIPLIER from entry; the live take-profit order on the instrument
    # scales that underlying move by the instrument's actual leverage.
    # The stop loss is confirmed when CONFIRMATION_COUNT + 1 consecutive completed bars close beyond the level
    CONFIRMATION_COUNT: int = 3


@dataclass(frozen=True)
class Pullback:
    # The percentage of the maximum profit that must be lost before a pullback is confirmed
    # Example: 0.4 means that if the maximum profit is 10% and the current profit is 6%, a pullback is confirmed
    # The pullback is confirmed if the price falls below the buy price by the percentage for a certain number of times
    # It only starts once the profit exceeds the source's pullback trigger (ExitLevels.pullback_trigger)
    VALUE: float = 0.0
    CONFIRMATION_COUNT: int = 2


@dataclass(frozen=True)
class Time:
    # The time range during which the trading is active
    START: time = time(9, 45)
    END: time = time(17, 15)


@dataclass(frozen=True)
class FixedRule:
    # One rule frozen on START and never re-ranked. STRATEGY's indicators run on SIGNAL_RESOLUTION bars built from
    # the 2m cache, faded when INVERTED (an
    # indicator LONG opens SHORT and vice versa), and act on the 2m bar that completes each coarse bar; exits are
    # managed on 2m with the levels below.
    # Traded live when LIVE_SIGNAL_SOURCE is "fixed_rule", otherwise logged as [PAPER]. task_end_of_day replays the
    # session into logs/paper_trades_<NAME>_fixed_rule.json; task_end_of_week sends the running total since START;
    # development.py replays the rule over the whole cache.
    # Chosen in the 2026-11-17 study: in-sample 2024-05..2026-11 151 trades, +1.0 capital since 2025-01 (t 2.2),
    # 9 of 11 quarters positive, but the study's luck-only test could not rule out chance (p 0.76 for the family).
    # At ~7 trades a month, judging it needs roughly 100+ forward trades. Changing the rule restarts the test.
    STRATEGY: tuple[str, ...] = ("Cycles-EBSW", "Momentum-MACD_DEMA", "Overlap-LINREG")
    INVERTED: bool = True
    SIGNAL_RESOLUTION: str = "30min"
    TAKE_PROFIT: float = 0.07
    STOP_LOSS: float = 0.12
    PULLBACK_TRIGGER: float = 0.07 / 2  # as the study simulated it: half the take profit
    # Calendar days of 2m history before a session that warm up the indicators
    WARMUP_DAYS: int = 60
    START: date = date(2026, 11, 18)


@dataclass(frozen=True)
class WeightedScore:
    # Every indicator on every resolution votes: "dir" is +1 on its LONG signal, -1 on SHORT, 0 otherwise; "exit" is 1
    # on its EXIT signal (only with USE_EXIT_VOTES). Intraday RESOLUTIONS are built from the 2m cache (a coarse bar
    # counts from the 2m bar that completes it); USE_DAILY adds the 1d cache's indicators as of the previous session.
    # A weight per vote is fitted (L1: useless votes get weight 0) to the underlying move over the next
    # HORIZON_BARS 2m bars (exit fill, capped at TIME.END; clipped at TARGET_CLIP_SD standard deviations, 0: off), on
    # the TRAIN_DAYS calendar days before training (0: all cached history). The score is the weighted sum;
    # BULL above the training ENTRY_QUANTILE of |score - median|, BEAR below its negative, EXIT once |score - median|
    # falls under EXIT_FRACTION of that threshold (0: never). A position is held exactly HORIZON_BARS completed bars,
    # the move the score predicts, then sold at the next open (or at TIME.END); signals are ignored meanwhile.
    # TAKE_PROFIT / STOP_LOSS / PULLBACK_TRIGGER of None turn those exits off, as calibrated.
    # The model lives in config/<NAME>_weighted_model.json:
    # task_end_of_week refits it, and its weights can be edited by hand between refits.
    # Walk-forward 2026-11-18 (weekly refit, 100 out-of-sample weeks): the score predicts the next 30-120 minutes
    # (correlation +0.02 to +0.07, t 2.2-3.4) but the move behind its strongest readings (~0-2 bp of the underlying)
    # does not cover the 2 bp the spread costs; every exit variant lost after costs.
    # Calibration 2026-11-18: 1,500 settings x 7 thresholds, weekly refits, chosen on 2024-11..2025-12 by the score's
    # correlation with the move, confirmed once on 2026-01..11. These defaults (60-bar horizon, direction votes of
    # 30min/60min/1d only, ~250 sessions, clipped target) doubled the out-of-sample correlation: 2025 +0.088 (t 3.3),
    # 2026 +0.060 (t 2.0), vs +0.03 before; every neighbouring setting stayed positive in 2026. Trading the top 1%
    # with an exit exactly HORIZON_BARS later: 2026 18 trades, +8.6 bp gross, +0.12 capital net, too few to call;
    # selecting settings by trading profit instead did not survive 2026. Single weights shuffle between correlated
    # votes from refit to refit (0-17% keep their sign), so read the score, not one weight.
    RESOLUTIONS: tuple[str, ...] = ("30min", "60min")
    USE_DAILY: bool = True
    USE_EXIT_VOTES: bool = False
    HORIZON_BARS: int = 60
    TARGET_CLIP_SD: float = 3.0
    TRAIN_DAYS: int = 365
    # L1 strengths tried (on standardized votes, target in bp); the one with the best correlation on the last
    # VALIDATION_SHARE of the training data (still before the model's use) is refitted on all of it
    ALPHAS: tuple[float, ...] = (0.1, 0.3, 1.0, 3.0)
    VALIDATION_SHARE: float = 0.2
    ENTRY_QUANTILE: float = 0.99
    EXIT_FRACTION: float = 0.0
    TAKE_PROFIT: float | None = None
    STOP_LOSS: float | None = None
    PULLBACK_TRIGGER: float | None = None
    # Calendar days of 2m history the live loop and the paper replay compute votes on
    WARMUP_DAYS: int = 60


@dataclass(frozen=True)
class TradeStrategies:
    NAME: str = "OMX"
    ACCOUNT_ID: str = "754762"

    DATA_SOURCE: str = "avanza"
    RESOLUTION: str = "2m"
    MULTIPLIER: int = 10
    SPREAD_MAX: float = 0.004  # 0.4%: watchlist ceiling for an instrument's spread
    # The only trading cost: the spread, paid once per trade on the sale (the instrument is sold this fraction below
    # its actual price; the buy fills at the actual price). Charged on every backtest trade.
    SPREAD_DEFAULT: float = 0.002

    AVA: str = "19002"
    YAHOO: str = "^OMX"

    STOP_LOSS: StopLoss = field(default_factory=StopLoss)
    PULLBACK: Pullback = field(default_factory=Pullback)
    TIME: Time = field(default_factory=Time)
    FIXED_RULE: FixedRule = field(default_factory=FixedRule)
    WEIGHTED_SCORE: WeightedScore = field(default_factory=WeightedScore)
    # Which signal source task_trade trades: "fixed_rule", "weighted", or None (no orders: every source is only
    # logged as [PAPER]). Every source is also replayed into a paper journal at end of day. Only switch after a
    # source's paper journal shows a forward edge.
    LIVE_SIGNAL_SOURCE: str | None = None

    BUDGET: float = 1.0

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
