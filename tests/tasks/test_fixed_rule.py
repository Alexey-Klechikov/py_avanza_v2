from unittest import TestCase
from unittest.mock import patch

import numpy as np
import pandas as pd

from services.ta.strategies.models.signal import Signal
from tasks import fixed_rule


def _history(end: str = "2026-11-16 17:28") -> pd.DataFrame:
    index = pd.date_range("2026-11-16 09:00", end, freq="2min")
    close = np.linspace(1000, 1010, len(index))

    return pd.DataFrame(
        {"Open": close, "High": close + 1, "Low": close - 1, "Close": close, "Volume": 0},
        index=index,
    )


def _mark_long_on(coarse_labels: list[str]):
    def mark(coarse: pd.DataFrame, *_, **__) -> None:
        for column in ("LONG", "SHORT", "EXIT"):
            coarse[column] = np.nan
        coarse.loc[coarse.index.isin(pd.to_datetime(coarse_labels)), "LONG"] = 1.0

    return mark


class Test_FixedRule(TestCase):
    def _signal_bars(self, coarse_labels: list[str], history: pd.DataFrame | None = None) -> pd.DataFrame:
        with (
            patch.object(fixed_rule, "get_indicators", return_value={}),
            patch.object(fixed_rule, "Strategy"),
            patch.object(fixed_rule, "mark_strategy_signals", side_effect=_mark_long_on(coarse_labels)),
        ):
            return fixed_rule.fixed_rule_signal_bars(_history() if history is None else history)

    def test_coarse_signal_acts_on_completing_bar_and_is_faded(self):
        bars = self._signal_bars(["2026-11-16 10:00"])

        assert list(bars.index[bars["SHORT"].notna()]) == [pd.Timestamp("2026-11-16 10:28")]
        assert bars["LONG"].isna().all()

    def test_trading_window_applies_on_completing_bar(self):
        # 09:00 completes at 09:28 (before START); 09:30 completes at 09:58 (inside the window)
        bars = self._signal_bars(["2026-11-16 09:00", "2026-11-16 09:30"])

        assert list(bars.index[bars["SHORT"].notna()]) == [pd.Timestamp("2026-11-16 09:58")]

    def test_coarse_bar_in_progress_never_signals(self):
        bars = self._signal_bars(["2026-11-16 10:00"], history=_history(end="2026-11-16 10:20"))

        assert bars["SHORT"].isna().all()

    def test_live_signal_is_the_newest_bar(self):
        with (
            patch.object(fixed_rule, "get_indicators", return_value={}),
            patch.object(fixed_rule, "Strategy"),
            patch.object(fixed_rule, "mark_strategy_signals", side_effect=_mark_long_on(["2026-11-16 10:00"])),
        ):
            assert fixed_rule.fixed_rule_signal(_history(end="2026-11-16 10:28")) == Signal.SHORT
            assert fixed_rule.fixed_rule_signal(_history(end="2026-11-16 10:30")) is None
