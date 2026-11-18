import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, TypeAdapter

from config import SETTINGS
from services.storage.operators import Storage
from services.ta.strategies.signals import SIGNAL_COLUMNS
from services.trading.tracked_position import ExitLevels
from tasks.backtest.bars import BAR_COLUMNS, bar_index
from tasks.backtest.model import WEIGHTED_LEVELS, load_model, weighted_signal_bars
from tasks.backtest.simulator import BarSimulator
from tasks.backtest.votes import vote_frame
from tasks.fixed_rule import FIXED_RULE_LEVELS, fixed_rule_signal_bars
from utils.logger.operators import get_logger

log = get_logger()


class PaperTrack(Enum):
    FIXED_RULE = "fixed_rule"
    WEIGHTED = "weighted"


class PaperSession(BaseModel):
    """One session of a signal source as simulated; returns are fractions of position capital."""

    trades: int
    wins: int
    capital_return: float
    trade_returns: list[float]


JOURNAL_ADAPTER = TypeAdapter(dict[date, PaperSession])
LOGS_DIR = Path(__file__).resolve().parents[2] / "logs"
TRACK_WARMUP_DAYS = {
    PaperTrack.FIXED_RULE: SETTINGS.FIXED_RULE.WARMUP_DAYS,
    PaperTrack.WEIGHTED: SETTINGS.WEIGHTED_SCORE.WARMUP_DAYS,
}


def _journal_path(track: PaperTrack) -> Path:
    return LOGS_DIR / f"paper_trades_{SETTINGS.NAME}_{track.value}.json"


def _read_journal(track: PaperTrack) -> dict[date, PaperSession]:
    path = _journal_path(track)
    if not path.exists():
        return {}

    return JOURNAL_ADAPTER.validate_json(path.read_bytes())


def _write_journal(track: PaperTrack, journal: dict[date, PaperSession]) -> None:
    LOGS_DIR.mkdir(exist_ok=True)
    payload = JOURNAL_ADAPTER.dump_python(dict(sorted(journal.items())), mode="json")
    _journal_path(track).write_text(json.dumps(payload, indent=2))


def _track_signal_bars(track: PaperTrack, history: pd.DataFrame) -> tuple[pd.DataFrame, ExitLevels] | None:
    if track == PaperTrack.FIXED_RULE:
        return fixed_rule_signal_bars(history), FIXED_RULE_LEVELS

    model = load_model()
    if model is None:
        log.warning("No weighted model file yet (task_end_of_week trains it); weighted paper track skipped")
        return None

    votes = vote_frame(history, Storage(resolution="1d").read())
    return weighted_signal_bars(model, votes, history), WEIGHTED_LEVELS


def replay(bars: pd.DataFrame, sessions: set[date], levels: ExitLevels) -> dict[date, PaperSession]:
    """Simulate `sessions` of signal `bars` (BAR_COLUMNS + SIGNAL_COLUMNS). Positions never carry overnight, so one
    pass over the sessions' bars equals replaying each session alone."""
    trade_returns: dict[date, list[float]] = defaultdict(list)
    simulator = BarSimulator(levels=levels)

    session_bars = bars.loc[pd.Series(bar_index(bars).date).isin(sessions).to_numpy(), BAR_COLUMNS + SIGNAL_COLUMNS]
    for index, bar in session_bars.iterrows():
        timestamp: datetime = index.to_pydatetime()  # type: ignore
        trade_returns[timestamp.date()].extend(trade.capital_return for trade in simulator.step(bar, timestamp))

    return {
        session: PaperSession(
            trades=len(trade_returns[session]),
            wins=sum(trade_return > 0 for trade_return in trade_returns[session]),
            capital_return=sum(trade_returns[session]),
            trade_returns=trade_returns[session],
        )
        for session in sorted(sessions)
    }


def replay_fixed_rule(history: pd.DataFrame) -> dict[date, PaperSession]:
    """Every session of `history` after the first WARMUP_DAYS, as the fixed rule would have traded it."""
    first_session = history.index[0].date() + timedelta(days=SETTINGS.FIXED_RULE.WARMUP_DAYS)
    sessions = {session for session in bar_index(history).date if session >= first_session}

    return replay(fixed_rule_signal_bars(history), sessions, FIXED_RULE_LEVELS)


def forward_summary(track: PaperTrack) -> str:
    """Running total of the track's journal (the fixed rule's from FIXED_RULE.START)."""
    start = SETTINGS.FIXED_RULE.START if track == PaperTrack.FIXED_RULE else date.min
    sessions = [paper for session, paper in _read_journal(track).items() if session >= start]
    trades = sum(paper.trades for paper in sessions)
    wins = sum(paper.wins for paper in sessions)
    total_return = sum(paper.capital_return for paper in sessions)

    return (
        f"Paper {track.value}: {len(sessions)} sessions, {trades} trades, {wins} profitable, "
        f"capital return {round(100 * total_return, 2)}%"
    )


def paper_trade_session(session: date) -> None:
    """Replay every paper track on `session` from the 2m cache and record it in its journal (no orders).

    Run after the session's bars are cached. Re-running a session replaces its journal entries.
    """
    cached_bars = Storage().read()
    end = pd.Timestamp(session + timedelta(days=1))
    if not (bar_index(cached_bars).date == session).any():
        log.warning(f"No cached {SETTINGS.RESOLUTION} bars for {session}; nothing to paper trade")
        return

    for track in PaperTrack:
        log.warning(f"TASK: Paper trade {SETTINGS.NAME} | {track.value} | {session}")
        start = pd.Timestamp(session - timedelta(days=TRACK_WARMUP_DAYS[track]))
        history = cached_bars[(cached_bars.index >= start) & (cached_bars.index < end)]
        signal_source = _track_signal_bars(track, history)
        if signal_source is None:
            continue

        signal_bars, levels = signal_source
        paper = replay(signal_bars, {session}, levels)[session]
        log.info(f"Paper {track.value} {session}: {paper.trades} trades, {round(100 * paper.capital_return, 2)}%")

        journal = _read_journal(track)
        journal[session] = paper
        _write_journal(track, journal)
        log.warning(forward_summary(track))
