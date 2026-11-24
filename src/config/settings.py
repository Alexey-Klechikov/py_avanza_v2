from dataclasses import dataclass, field
from datetime import time


@dataclass(frozen=True)
class SettingsWatchlist:
    INSTRUMENT_DIRECTIONS = {"Kort": "BEAR", "Lång": "BULL"}

    TRADING_PERSPECTIVE_PREFIX = "DT"
    WATCHLIST_NAME_PARTS = 4

    LEVERAGE_LOWER_MULTIPLIER = 0.8
    LEVERAGE_UPPER_MULTIPLIER = 1.2

    MIN_SPREAD_PERCENT = 0.05
    MAX_SPREAD_PERCENT = 0.4
    MIN_PRICE = 1
    MAX_PRICE = 300

    SEARCH_WARRANT_PREFIX = {"BULL": "L", "BEAR": "S"}


@dataclass(frozen=True)
class Exits:
    # How a position ends before the day's end, in the backtest and the live loop alike (ExitLevels). Levels are moves
    # of the instrument at the nominal MULTIPLIER (0.05: 0.5% of TSLA at x10), set on the underlying at
    # level / MULTIPLIER from the entry; None turns a rule off. The take-profit is a resting order (live: on the
    # instrument, scaled by its actual leverage). A position is also held at most WEIGHTED_SCORE.HORIZON_BARS
    # completed bars, the move the score predicts, and new signals are ignored while it is held.
    # Chosen 2026-11-19: TAKE_PROFIT x STOP_LOSS grid (84 combinations, hold on and off) on calibration data before
    # the holdout, where no combination was significant alone and a tight stop helped most consistently; three
    # candidates fixed in advance were then run once on the holdout (2025-11-19..2026-11-18, 251 sessions): hold only
    # +1.24% net/trade (t 1.4, max drawdown 0.62), stop 5% +1.21% (t 1.7, 0.44), take-profit 15% + stop 5% +1.18%
    # (t 1.9, 0.44, 156 trades). One year with t < 2: the paper journal decides. A pullback (trailing) exit was
    # removed 2026-11-19: on calibration data it only cut winners (the earlier and tighter, the worse: t 1.39 -> 0.27).
    TAKE_PROFIT: float | None = 0.15
    STOP_LOSS: float | None = 0.05
    STOP_LOSS_CONFIRMATIONS: int = 3  # the stop fires after this many + 1 consecutive closes beyond its level


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
    # BULL above the training ENTRY_QUANTILE of |score - median|, BEAR below its negative. Positions exit by EXITS
    # (TradeSettings), held at most HORIZON_BARS completed bars.
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
    # Chosen 2026-11-21 (was 0.95): walk-forward over 850 TSLA sessions (2023-07..2026-11-20, refit every 5, live
    # EXITS) at quantiles 0.75-0.99. Net per trade is flat (~+1%) from the top 25% to the top 5% of scores and worse
    # beyond, so a stricter threshold only drops trades: 0.85 +0.98%/trade, 1.3 trades/day, t 3.8 (before / from
    # 2025-11-19: t 3.0 / 2.5), 1 losing quarter of 14; 0.95 +0.87%, 0.6/day, t 2.3 (1.8 / 1.6), 5 losing quarters.
    # Picked among 8 levels on all data, holdout included, so the paper journal still decides.
    ENTRY_QUANTILE: float = 0.85
    # Calendar days of 2m history the live loop and the paper replay compute votes on
    WARMUP_DAYS: int = 60


@dataclass(frozen=True)
class TradeSettings:
    NAME: str = "TSLA"
    # Avanza names the traded products after the company, not the ticker ("BULL TESLA X10 AVA 3"): watchlist searches,
    # positions and orders are matched by this
    PRODUCT_NAME: str = "TESLA"
    ACCOUNT_ID: str = "754762"

    DATA_SOURCE: str = "avanza"
    RESOLUTION: str = "2m"
    MULTIPLIER: int = 10  # nominal leverage of the traded certificates; watchlists accept it within the tolerance
    # The only trading cost the backtest charges: the spread, paid once per trade on the sale (the instrument is sold
    # this fraction below its actual price; the buy fills at the actual price)
    BACKTEST_SPREAD: float = 0.002

    AVA: str = "238449"
    YAHOO: str = "TSLA"

    TIME: Time = field(default_factory=Time)
    EXITS: Exits = field(default_factory=Exits)
    WEIGHTED_SCORE: WeightedScore = field(default_factory=WeightedScore)
    # True: task_trade places orders on the weighted score's signals. False: its signals are only logged as [PAPER].
    # Either way task_end_of_day replays the session into logs/paper_trades_<NAME>_weighted.json.
    # Switched on 2026-11-19, before the forward paper journal had confirmed the edge (holdout t < 2, see Exits).
    # config/TSLA_weighted_model.json was refitted on the current INDICATORS then (commit 2a13b81, trained
    # 2025-11-18..2026-11-18; a refit on 2026-11-19 reproduced its weights exactly).
    LIVE_ORDERS: bool = True

    BUDGET: float = 1.0  # share of the account's total value put into one position

    # Indicators that vote in the weighted score: each needs a LONG/SHORT direction signal
    INDICATORS: dict[str, dict[str, dict[str, int | float | str]]] = field(
        default_factory=lambda: {
            "Trend": {
                "ADX": {"length": 7, "lensig": 20, "mamode": "hma"},
                "TII": {"length_sma": 16, "length_signal": 4},
                "PSAR": {"acceleration": 0.01, "maximum": 0.2},
            },
            "Overlap": {
                "LINREG": {"length": 16, "limit": 0.2},
                "SLOPE": {"length": 8, "limit": 0.1},
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
                "PVT": {"drift": 16, "length_sma": 16, "length_divergence": 24},
                "ADOSC": {"fast": 4, "slow": 8, "length_divergence": 30},
                "CMF": {"length": 28, "length_divergence": 32},
                "KVO": {"fast": 22, "slow": 55, "signal": 10, "mamode": "rma", "length_divergence": 30},
            },
        },
    )
