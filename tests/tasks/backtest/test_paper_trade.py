from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import numpy as np
import pandas as pd

from tasks.backtest import paper_trade
from tasks.backtest.bars import add_execution_columns
from tasks.backtest.paper_trade import PaperSession
from tasks.fixed_rule import FIXED_RULE_LEVELS

SESSION = date(2026, 11, 16)


def _history() -> pd.DataFrame:
    index = pd.date_range("2026-11-16 09:00", "2026-11-16 17:28", freq="2min")
    close = np.full(len(index), 1000.0)

    return pd.DataFrame({"Open": close, "High": close, "Low": close, "Close": close, "Volume": 0}, index=index)


def _signal_bars(long_at: str) -> pd.DataFrame:
    bars = _history().drop(columns="Volume")
    bars[["LONG", "SHORT", "EXIT"]] = np.nan
    bars.loc[pd.Timestamp(long_at), "LONG"] = 1000.0
    add_execution_columns(bars)

    return bars


class Test_PaperTrade(TestCase):
    def test_replay_closes_the_position_by_day_end(self):
        paper = paper_trade.replay(_signal_bars(long_at="2026-11-16 10:28"), {SESSION}, FIXED_RULE_LEVELS)[SESSION]

        assert paper.trades == 1 and paper.wins == 0
        assert paper.capital_return == paper.trade_returns[0] < 0  # flat price: only the spread is lost

    def test_session_replaces_journal_entries_per_track(self):
        first = PaperSession(trades=1, wins=0, capital_return=-0.01, trade_returns=[-0.01])
        second = PaperSession(trades=2, wins=1, capital_return=0.02, trade_returns=[0.03, -0.01])
        replays = [{SESSION: first}, {SESSION: first}, {SESSION: second}, {SESSION: second}]
        with TemporaryDirectory() as directory:
            with (
                patch.object(paper_trade, "LOGS_DIR", Path(directory)),
                patch.object(paper_trade.Storage, "read", return_value=_history()),
                patch.object(paper_trade, "_track_signal_bars", side_effect=lambda track, history: (history, None)),
                patch.object(paper_trade, "replay", side_effect=replays),
            ):
                paper_trade.paper_trade_session(SESSION)
                paper_trade.paper_trade_session(SESSION)

                journals = {track: paper_trade._read_journal(track) for track in paper_trade.PaperTrack}

        for journal in journals.values():
            assert list(journal) == [SESSION]
            assert journal[SESSION].trades == 2

    def test_track_without_model_is_skipped(self):
        with (
            patch.object(paper_trade, "load_model", return_value=None),
            patch.object(paper_trade.Storage, "read", return_value=_history()),
        ):
            assert paper_trade._track_signal_bars(paper_trade.PaperTrack.WEIGHTED, _history()) is None

    def test_session_without_bars_is_skipped(self):
        with (
            patch.object(paper_trade.Storage, "read", return_value=_history()),
            patch.object(paper_trade, "_track_signal_bars") as track_signal_bars,
        ):
            paper_trade.paper_trade_session(date(2026, 11, 17))

        track_signal_bars.assert_not_called()
