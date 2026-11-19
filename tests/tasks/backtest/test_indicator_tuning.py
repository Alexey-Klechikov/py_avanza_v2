from datetime import date
from unittest import TestCase
from unittest.mock import patch

import numpy as np
import pandas as pd

from config import SETTINGS
from tasks.backtest import indicator_tuning
from tasks.backtest.indicator_tuning import IndicatorGrid, full_training_sessions, tune_indicator
from tasks.backtest.paper_trade import PaperSession
from tasks.backtest.weighted_walk_forward import WeightedWalkForward


def _walk_forward(correlations: list[float]) -> WeightedWalkForward:
    paper = PaperSession(trades=2, wins=1, capital_return=0.01, trade_returns=[0.02, -0.01])
    return WeightedWalkForward(sessions={date(2026, 1, 2): paper}, correlations=correlations, kept_votes=[3])


class Test_IndicatorGrid(TestCase):
    def test_lists_are_searched_and_scalars_stay_fixed(self):
        grid = IndicatorGrid(
            category="Trend",
            name="ADX",
            params={"length": [7, 9], "lensig": [10, 14], "mamode": "hma"},
        )

        candidates = grid.candidates()

        assert len(candidates) == 4
        assert {"length": 9, "lensig": 10, "mamode": "hma"} in candidates


class Test_TuneIndicator(TestCase):
    def test_ranks_by_edge_and_restores_the_settings(self):
        current = SETTINGS.INDICATORS["Trend"]["ADX"]
        grid = IndicatorGrid(category="Trend", name="ADX", params={"length": [7, 9], "lensig": 14, "mamode": "hma"})
        seen: list[dict | None] = []

        def fake_walk_forward(history, daily, test_sessions, refit_sessions):
            params = SETTINGS.INDICATORS["Trend"].get("ADX")
            seen.append(params)
            strong = params is not None and params.get("length") == 9
            return _walk_forward([0.05, 0.06, 0.04] if strong else [0.01, -0.01, 0.02])

        with (
            patch.object(indicator_tuning, "weighted_walk_forward", side_effect=fake_walk_forward),
            patch.object(indicator_tuning, "full_training_sessions", return_value=10),
        ):
            results = tune_indicator(pd.DataFrame(), pd.DataFrame(), grid)

        assert seen[0] == current and seen[1] is None  # current first, then the indicator off
        assert results[0].params == {"length": 9, "lensig": 14, "mamode": "hma"}
        assert results[0].trades == 2 and results[0].net_return_per_trade == 0.005
        assert SETTINGS.INDICATORS["Trend"]["ADX"] == current


class Test_FullTrainingSessions(TestCase):
    def test_counts_sessions_after_warmup_and_training(self):
        settings = SETTINGS.WEIGHTED_SCORE
        days = pd.bdate_range("2024-01-01", periods=600)
        history = pd.DataFrame({"Close": np.ones(len(days))}, index=days)
        first_full = days[0] + pd.Timedelta(days=settings.WARMUP_DAYS + settings.TRAIN_DAYS)

        assert full_training_sessions(history) == int((days >= first_full).sum())


class Test_UnknownCategory(TestCase):
    def test_raises_without_touching_the_settings(self):
        categories = set(SETTINGS.INDICATORS)
        grid = IndicatorGrid(category="Unknown", name="X", params={"length": [1]})

        with self.assertRaisesRegex(ValueError, "Unknown indicator category"):
            tune_indicator(pd.DataFrame(), pd.DataFrame(), grid)

        assert set(SETTINGS.INDICATORS) == categories
