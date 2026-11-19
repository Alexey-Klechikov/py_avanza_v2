import json
from datetime import date
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd
from pydantic import BaseModel

from config import SETTINGS
from services.ta.strategies.models.signal import Signal
from services.ta.strategies.signals import SIGNAL_COLUMNS
from services.trading.tracked_position import ExitLevels
from tasks.shared.bars import add_execution_columns, bar_index, is_at_or_after_trading_end, is_in_trading_window
from tasks.shared.votes import vote_frame
from utils.logger.operators import get_logger

log = get_logger()


class WeightedModel(BaseModel):
    """Weights of the votes (only the non-zero ones) and the score thresholds, see SETTINGS.WEIGHTED_SCORE.

    score = sum(weight * vote) + intercept: the expected underlying move (bp) over horizon_bars. Signals compare
    score - center against entry_threshold: BULL above, BEAR below its negative.
    """

    weights: dict[str, float]
    intercept: float
    center: float
    entry_threshold: float
    horizon_bars: int
    alpha: float
    trained_from: date
    trained_to: date

    def score(self, votes: pd.DataFrame) -> pd.Series:
        weights = pd.Series(self.weights, dtype=float)

        return votes.reindex(columns=weights.index, fill_value=0) @ weights + self.intercept

    @property
    def bull_above(self) -> float:
        """Scores above this signal BULL."""
        return self.center + self.entry_threshold

    @property
    def bear_below(self) -> float:
        """Scores below this signal BEAR."""
        return self.center - self.entry_threshold


class WeightedReading(NamedTuple):
    """The model's signal and score (expected underlying move over horizon_bars, bp) on one bar."""

    signal: Signal | None
    score: float


MODEL_PATH = Path(__file__).resolve().parents[2] / "config" / f"{SETTINGS.NAME}_weighted_model.json"

WEIGHTED_LEVELS = ExitLevels(
    take_profit=SETTINGS.WEIGHTED_SCORE.TAKE_PROFIT,
    stop_loss=SETTINGS.WEIGHTED_SCORE.STOP_LOSS,
    pullback_trigger=SETTINGS.WEIGHTED_SCORE.PULLBACK_TRIGGER,
    hold_bars=SETTINGS.WEIGHTED_SCORE.HORIZON_BARS,
)


def forward_move_bp(bars: pd.DataFrame, horizon_bars: int) -> np.ndarray:
    """Underlying move (bp) from the next open to the fill of an exit `horizon_bars` later, or at the session's exit
    bar (the first bar closing at or after SETTINGS.TIME.END, else its last bar) when that comes first."""
    times = bar_index(bars)
    day_codes = pd.factorize(times.date)[0]
    positions = np.arange(len(bars))
    at_or_after_end = np.where(is_at_or_after_trading_end(times), positions, len(bars))
    by_day = pd.DataFrame({"end": at_or_after_end, "last": positions}).groupby(day_codes)
    exit_bars = np.minimum(by_day["end"].transform("min").to_numpy(), by_day["last"].transform("max").to_numpy())
    next_open = bars["Next Open"].to_numpy()

    return (next_open[np.minimum(positions + horizon_bars, exit_bars)] / next_open - 1) * 1e4


def _lasso(gram: np.ndarray, correlation: np.ndarray, alpha: float, max_sweeps: int = 1000) -> np.ndarray:
    """Coordinate descent for min 1/2 w'Gw - c'w + alpha |w|_1 (the L1 linear fit on standardized votes with unit
    variance, in Gram form)."""
    weights = np.zeros(len(correlation))
    for _ in range(max_sweeps):
        largest_change = 0.0
        for j in range(len(correlation)):
            rho = correlation[j] - gram[j] @ weights + gram[j, j] * weights[j]
            new_weight = np.sign(rho) * max(abs(rho) - alpha, 0.0) / gram[j, j]
            largest_change = max(largest_change, abs(new_weight - weights[j]))
            weights[j] = new_weight
        if largest_change < 1e-7:
            break

    return weights


def _choose_alpha(standardized: np.ndarray, target: np.ndarray) -> float:
    """The ALPHAS value whose fit on the earlier part of the data correlates best with the later part."""
    fit_rows = int(len(target) * (1 - SETTINGS.WEIGHTED_SCORE.VALIDATION_SHARE))
    fit_votes, validation_votes = standardized[:fit_rows], standardized[fit_rows:]
    gram = fit_votes.T @ fit_votes / fit_rows
    correlation = fit_votes.T @ target[:fit_rows] / fit_rows

    best_alpha, best_correlation = SETTINGS.WEIGHTED_SCORE.ALPHAS[0], -np.inf
    for alpha in SETTINGS.WEIGHTED_SCORE.ALPHAS:
        prediction = validation_votes @ _lasso(gram, correlation, alpha)
        validation_correlation = np.corrcoef(prediction, target[fit_rows:])[0, 1] if prediction.std() > 0 else -np.inf
        if validation_correlation > best_correlation:
            best_alpha, best_correlation = alpha, validation_correlation

    return best_alpha


def fit_model(votes: pd.DataFrame, bars: pd.DataFrame, is_train: np.ndarray) -> WeightedModel:
    """Fit the weights on the `is_train` rows of `votes` inside the trading window (`bars`: 2m bars with
    "Next Open", chronological)."""
    settings = SETTINGS.WEIGHTED_SCORE
    target = forward_move_bp(bars, settings.HORIZON_BARS)
    is_fit_row = is_train & is_in_trading_window(bar_index(bars)) & np.isfinite(target)
    if not is_fit_row.any():
        raise ValueError("No training bars: the fit window lies inside the warm-up or before the cached history")

    train_votes = votes.to_numpy(dtype=np.float64)[is_fit_row]
    vote_mean, vote_sd = train_votes.mean(0), train_votes.std(0)
    has_variance = vote_sd > 0
    standardized = (train_votes[:, has_variance] - vote_mean[has_variance]) / vote_sd[has_variance]
    train_target = target[is_fit_row]
    if settings.TARGET_CLIP_SD:
        limit = settings.TARGET_CLIP_SD * train_target.std()
        train_target = np.clip(train_target, -limit, limit)
    target_mean = train_target.mean()
    centered_target = train_target - target_mean

    # macOS Accelerate BLAS emits spurious matmul warnings on finite inputs; the result is checked instead
    with np.errstate(all="ignore"):
        alpha = _choose_alpha(standardized, centered_target)
        gram = standardized.T @ standardized / len(standardized)
        weights = _lasso(gram, standardized.T @ centered_target / len(standardized), alpha)
        train_score = standardized @ weights + target_mean
    if not (np.isfinite(weights).all() and np.isfinite(train_score).all()):
        raise ValueError("Weighted score fit produced non-finite weights")

    center = float(np.median(train_score))
    entry_threshold = float(np.quantile(np.abs(train_score - center), settings.ENTRY_QUANTILE))
    vote_weights = weights / vote_sd[has_variance]
    vote_names = votes.columns[has_variance]
    trained_days = bar_index(bars)[is_fit_row].date

    return WeightedModel(
        weights={name: float(weight) for name, weight in zip(vote_names, vote_weights) if weight != 0},
        intercept=float(target_mean - (vote_mean[has_variance] / vote_sd[has_variance]) @ weights),
        center=center,
        entry_threshold=entry_threshold,
        horizon_bars=settings.HORIZON_BARS,
        alpha=alpha,
        trained_from=trained_days[0],
        trained_to=trained_days[-1],
    )


def weighted_signal_bars(model: WeightedModel, votes: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    """2m bars (OHLC, "Next Open", "Day End", SIGNAL_COLUMNS) carrying the model's signals."""
    deviation = model.score(votes) - model.center
    is_signal = {
        "LONG": deviation > model.entry_threshold,
        "SHORT": deviation < -model.entry_threshold,
    }

    bars = history[["Open", "High", "Low", "Close"]].copy()
    is_tradable = is_in_trading_window(bar_index(bars))
    for column in SIGNAL_COLUMNS:
        bars[column] = bars["Close"].where(is_signal[column] & is_tradable)

    add_execution_columns(bars)

    return bars


def weighted_signal(model: WeightedModel, closed_history: pd.DataFrame, daily: pd.DataFrame) -> WeightedReading:
    """The model's signal and score on the newest bar of `closed_history` (closed 2m bars, WARMUP_DAYS deep)."""
    votes = vote_frame(closed_history, daily)
    last_bar = weighted_signal_bars(model, votes, closed_history)[SIGNAL_COLUMNS].iloc[-1]

    return WeightedReading(signal=Signal.from_bar(*last_bar.notna()), score=float(model.score(votes).iloc[-1]))


def load_model() -> WeightedModel | None:
    if not MODEL_PATH.exists():
        return None

    return WeightedModel.model_validate_json(MODEL_PATH.read_text())


def save_model(model: WeightedModel) -> None:
    MODEL_PATH.write_text(json.dumps(model.model_dump(mode="json"), indent=2))


def train_weighted_model(history: pd.DataFrame, daily: pd.DataFrame) -> WeightedModel:
    """Fit on the last TRAIN_DAYS of `history` (0: all of it after the first WARMUP_DAYS), save, and log the votes
    that kept a weight."""
    settings = SETTINGS.WEIGHTED_SCORE
    votes = vote_frame(history, daily)
    bars = history[["Open", "High", "Low", "Close"]].copy()
    add_execution_columns(bars)

    first_day = bar_index(history)[0].normalize() + pd.Timedelta(days=settings.WARMUP_DAYS)
    if settings.TRAIN_DAYS:
        first_day = max(first_day, bar_index(history)[-1].normalize() - pd.Timedelta(days=settings.TRAIN_DAYS))

    model = fit_model(votes, bars, is_train=np.asarray(history.index >= first_day))
    save_model(model)

    log.warning(
        f"Weighted score: {len(model.weights)} of {votes.shape[1]} votes kept (alpha {model.alpha}), trained "
        f"{model.trained_from} - {model.trained_to}, entry |score| > {round(model.entry_threshold, 2)} bp",
    )
    for name, weight in sorted(model.weights.items(), key=lambda item: -abs(item[1])):
        log.info(f"Weight {round(weight, 3):+} bp: {name}")

    return model
