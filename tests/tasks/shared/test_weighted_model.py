from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import numpy as np
import pandas as pd

from services.ta.strategies.models.signal import Signal
from tasks.shared import weighted_model as model_module
from tasks.shared.bars import add_execution_columns
from tasks.shared.weighted_model import WeightedModel, _lasso, fit_model, forward_move_bp, weighted_signal_bars


def _bars_and_votes(days: int = 40) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Random walk whose next-bar move follows the sign of vote "useful"; "noise" votes carry nothing."""
    rng = np.random.default_rng(1)
    index = pd.DatetimeIndex(
        [
            ts
            for day in pd.bdate_range("2026-01-05", periods=days)
            for ts in pd.date_range(day + pd.Timedelta(hours=16), periods=150, freq="2min")
        ],
    )
    useful = rng.choice([-1.0, 1.0], len(index))
    returns = np.roll(useful, 1) * 4e-4 + rng.standard_normal(len(index)) * 2e-4
    close = 1000 * np.exp(np.cumsum(returns))
    bars = pd.DataFrame(
        {"Open": np.r_[close[0], close[:-1]], "High": close, "Low": close, "Close": close},
        index=index,
    )
    add_execution_columns(bars)
    votes = pd.DataFrame(
        {
            "useful": useful,
            "noise_a": rng.choice([-1.0, 0, 1], len(index)),
            "noise_b": rng.choice([0.0, 1], len(index)),
        },
        index=index,
    )

    return bars, votes


def _model(**overrides) -> WeightedModel:
    model = WeightedModel(
        weights={"a": 2.0},
        intercept=0.0,
        center=0.0,
        entry_threshold=1.0,
        horizon_bars=1,
        alpha=0.1,
        trained_from=date(2026, 1, 1),
        trained_to=date(2026, 1, 2),
    )
    return model.model_copy(update=overrides)


class Test_Lasso(TestCase):
    def test_recovers_sparse_weights(self):
        rng = np.random.default_rng(0)
        standardized = rng.standard_normal((5000, 6))
        target = standardized @ np.array([3.0, 0, 0, -2.0, 0, 0]) + rng.standard_normal(5000)
        n = len(target)

        weights = _lasso(standardized.T @ standardized / n, standardized.T @ target / n, alpha=0.3)

        assert np.allclose(weights[[0, 3]], [2.7, -1.7], atol=0.1)
        assert (weights[[1, 2, 4, 5]] == 0).all()


class Test_WeightedModel(TestCase):
    def test_fit_keeps_the_useful_vote_and_drops_noise(self):
        bars, votes = _bars_and_votes()
        settings = model_module.SETTINGS
        from dataclasses import replace

        weighted = replace(settings.WEIGHTED_SCORE, HORIZON_BARS=1, ALPHAS=(1.0,))
        with patch.object(model_module, "SETTINGS", replace(settings, WEIGHTED_SCORE=weighted)):
            model = fit_model(votes, bars, is_train=np.ones(len(bars), bool))

        assert set(model.weights) == {"useful"} and model.weights["useful"] > 0

    def test_signals_follow_the_thresholds(self):
        index = pd.date_range("2026-11-16 17:00", periods=4, freq="2min")
        history = pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0}, index=index)
        votes = pd.DataFrame({"a": [1.0, -1.0, 0.1, 0.4]}, index=index)  # scores 2, -2, 0.2, 0.8; entry 1

        bars = weighted_signal_bars(_model(), votes, history)
        signals = [Signal.from_bar(*row) for row in bars[["LONG", "SHORT"]].notna().to_numpy()]

        assert signals == [Signal.LONG, Signal.SHORT, None, None]

    def test_model_file_round_trip(self):
        with TemporaryDirectory() as directory:
            with patch.object(model_module, "MODEL_PATH", Path(directory) / "model.json"):
                assert model_module.load_model() is None
                model_module.save_model(_model())

                assert model_module.load_model() == _model()


class Test_FitWithoutTrainingBars(TestCase):
    def test_raises_a_clear_error(self):
        bars, votes = _bars_and_votes(days=2)
        add_execution_columns(bars)

        with self.assertRaisesRegex(ValueError, "No training bars"):
            fit_model(votes, bars, is_train=np.zeros(len(bars), bool))


class Test_ForwardMove(TestCase):
    def test_exit_is_capped_at_the_end_of_trading(self):
        index = pd.date_range("2026-11-16 21:40", periods=6, freq="2min")  # 21:40 .. 21:50, END is 21:45
        bars = pd.DataFrame({"Open": [100.0, 101, 102, 103, 104, 105], "Close": 0.0}, index=index)
        bars["Next Open"] = bars["Open"].shift(-1).fillna(105.0)

        moves = forward_move_bp(bars, horizon_bars=10)

        # the 21:44 bar is the first to close at or after END, as the live loop sees it: exits fill at its next
        # open (21:46 open, 103)
        assert np.allclose(moves[:3], (103 / bars["Next Open"].to_numpy()[:3] - 1) * 1e4)


class Test_WeightedReading(TestCase):
    def test_thresholds_in_score_units(self):
        model = _model(center=0.5, entry_threshold=2.0)

        assert (model.bull_above, model.bear_below) == (2.5, -1.5)

    def test_reading_carries_the_last_score(self):
        index = pd.date_range("2026-11-16 17:00", periods=3, freq="2min")
        history = pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0, "Volume": 0}, index=index)
        votes = pd.DataFrame({"a": [0.0, 0.0, 1.0]}, index=index)  # last score 2 > entry 1

        with patch.object(model_module, "vote_frame", return_value=votes):
            reading = model_module.weighted_signal(_model(), history, daily=pd.DataFrame())

        assert reading == (Signal.LONG, 2.0)
