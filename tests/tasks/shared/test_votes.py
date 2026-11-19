from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import numpy as np
import pandas as pd

from tasks.shared import votes as votes_module
from tasks.shared.bars import bar_index


def _history() -> pd.DataFrame:
    index = pd.date_range("2026-11-16 09:00", "2026-11-16 11:58", freq="2min")
    close = np.arange(len(index), dtype=float)

    return pd.DataFrame({"Open": close, "High": close, "Low": close, "Close": close, "Volume": 0}, index=index)


def _daily() -> pd.DataFrame:
    index = pd.to_datetime(["2026-11-13", "2026-11-16"])
    return pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": [100.0, 200.0], "Volume": 0}, index=index)


# One indicator: LONG while Close > 150 on daily bars, else on intraday bars LONG from Close >= 15
FAKE_SIGNAL = SimpleNamespace(LONG=lambda row: row["Close"] >= 15, SHORT=lambda row: row["Close"] < 15)


def _votes(history: pd.DataFrame, resolution: str) -> pd.DataFrame:
    with patch.object(
        votes_module,
        "add_indicators",
        return_value={"Trend": {"FAKE": SimpleNamespace(signal=FAKE_SIGNAL)}},
    ):
        return votes_module._intraday_votes(history, resolution)


class Test_Votes(TestCase):
    def test_coarse_vote_holds_from_its_completing_bar(self):
        votes = _votes(_history(), "30min")["30min:Trend-FAKE:dir"]

        # 09:00 bucket (closes 0..14 -> last close 14 -> SHORT) completes at 09:28; 09:30 (last close 29) at 09:58
        assert np.isnan(votes[pd.Timestamp("2026-11-16 09:26")])
        assert votes[pd.Timestamp("2026-11-16 09:28")] == -1
        assert votes[pd.Timestamp("2026-11-16 09:56")] == -1
        assert votes[pd.Timestamp("2026-11-16 09:58")] == 1

    def test_coarse_bar_in_progress_has_no_vote(self):
        history = _history().loc[:"2026-11-16 09:20"]

        assert _votes(history, "30min")["30min:Trend-FAKE:dir"].isna().all()

    def test_daily_vote_uses_the_previous_session(self):
        signal = SimpleNamespace(LONG=lambda row: row["Close"] > 150, SHORT=lambda row: row["Close"] <= 150)
        with patch.object(
            votes_module,
            "add_indicators",
            return_value={"Trend": {"FAKE": SimpleNamespace(signal=signal)}},
        ):
            votes = votes_module._daily_votes(bar_index(_history()), _daily())

        # 2026-11-16 uses 2026-11-13 (Close 100 -> SHORT), never its own row (Close 200)
        assert (votes["1d:Trend-FAKE:dir"] == -1).all()
