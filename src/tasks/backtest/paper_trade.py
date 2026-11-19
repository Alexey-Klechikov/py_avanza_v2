import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, TypeAdapter

from config import SETTINGS
from services.storage.operators import Storage
from services.ta.strategies.signals import SIGNAL_COLUMNS
from services.trading.tracked_position import ExitLevels
from tasks.backtest.simulator import BarSimulator
from tasks.shared.bars import BAR_COLUMNS, bar_index
from tasks.shared.votes import vote_frame
from tasks.shared.weighted_model import WEIGHTED_LEVELS, load_model, weighted_signal_bars
from utils.logger.operators import get_logger

log = get_logger()


class PaperSession(BaseModel):
    """One session of the weighted score as simulated; returns are fractions of position capital."""

    trades: int
    wins: int
    capital_return: float
    trade_returns: list[float]


JOURNAL_ADAPTER = TypeAdapter(dict[date, PaperSession])
LOGS_DIR = Path(__file__).resolve().parents[2] / "logs"


def _journal_path() -> Path:
    return LOGS_DIR / f"paper_trades_{SETTINGS.NAME}_weighted.json"


def _read_journal() -> dict[date, PaperSession]:
    path = _journal_path()
    if not path.exists():
        return {}

    return JOURNAL_ADAPTER.validate_json(path.read_bytes())


def _write_journal(journal: dict[date, PaperSession]) -> None:
    LOGS_DIR.mkdir(exist_ok=True)
    payload = JOURNAL_ADAPTER.dump_python(dict(sorted(journal.items())), mode="json")
    _journal_path().write_text(json.dumps(payload, indent=2))


def _weighted_signal_bars(history: pd.DataFrame) -> pd.DataFrame | None:
    model = load_model()
    if model is None:
        log.warning("No weighted model file yet (task_end_of_week trains it); paper replay skipped")
        return None

    votes = vote_frame(history, Storage(resolution="1d").read())
    return weighted_signal_bars(model, votes, history)


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


def forward_summary() -> str:
    """Running total of the weighted score's paper journal."""
    sessions = list(_read_journal().values())
    trades = sum(paper.trades for paper in sessions)
    wins = sum(paper.wins for paper in sessions)
    total_return = sum(paper.capital_return for paper in sessions)

    return (
        f"Paper weighted: {len(sessions)} sessions, {trades} trades, {wins} profitable, "
        f"capital return {round(100 * total_return, 2)}%"
    )


def paper_trade_session(session: date) -> None:
    """Replay the weighted score on `session` from the 2m cache and record it in the journal (no orders).

    Run after the session's bars are cached. Re-running a session replaces its journal entry.
    """
    cached_bars = Storage().read()
    if not (bar_index(cached_bars).date == session).any():
        log.warning(f"No cached {SETTINGS.RESOLUTION} bars for {session}; nothing to paper trade")
        return

    log.warning(f"TASK: Paper trade {SETTINGS.NAME} | weighted | {session}")
    history_start = pd.Timestamp(session - timedelta(days=SETTINGS.WEIGHTED_SCORE.WARMUP_DAYS))
    session_end = pd.Timestamp(session + timedelta(days=1))
    history = cached_bars[(cached_bars.index >= history_start) & (cached_bars.index < session_end)]
    signal_bars = _weighted_signal_bars(history)
    if signal_bars is None:
        return

    paper = replay(signal_bars, {session}, WEIGHTED_LEVELS)[session]
    log.info(f"Paper weighted {session}: {paper.trades} trades, {round(100 * paper.capital_return, 2)}%")

    journal = _read_journal()
    journal[session] = paper
    _write_journal(journal)
    log.warning(forward_summary())
