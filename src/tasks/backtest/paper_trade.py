import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, TypeAdapter

from config import SETTINGS
from services.storage.operators import Storage
from services.ta.strategies.signals import SIGNAL_COLUMNS
from tasks.backtest.bars import BAR_COLUMNS
from tasks.backtest.simulator import BarSimulator
from tasks.fixed_rule import FIXED_RULE_LEVELS, fixed_rule_signal_bars
from utils.logger.operators import get_logger

log = get_logger()


class PaperSession(BaseModel):
    """One session of the fixed rule (SETTINGS.FIXED_RULE) as simulated; returns are fractions of position capital."""

    trades: int
    wins: int
    capital_return: float
    trade_returns: list[float]


JOURNAL_PATH = Path(__file__).resolve().parents[2] / "logs" / f"paper_trades_{SETTINGS.NAME}.json"
JOURNAL_ADAPTER = TypeAdapter(dict[date, PaperSession])


def _replay(bars: pd.DataFrame, sessions: set[date]) -> dict[date, PaperSession]:
    """Simulate `sessions` of the fixed-rule signal bars. Positions never carry overnight, so one pass over the
    sessions' bars equals replaying each session alone."""
    trade_returns: dict[date, list[float]] = defaultdict(list)
    simulator = BarSimulator(levels=FIXED_RULE_LEVELS)

    session_bars = bars.loc[pd.Index(bars.index.date).isin(sessions), BAR_COLUMNS + SIGNAL_COLUMNS]
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


def _read_journal() -> dict[date, PaperSession]:
    if not JOURNAL_PATH.exists():
        return {}

    return JOURNAL_ADAPTER.validate_json(JOURNAL_PATH.read_bytes())


def _write_journal(journal: dict[date, PaperSession]) -> None:
    JOURNAL_PATH.parent.mkdir(exist_ok=True)
    payload = JOURNAL_ADAPTER.dump_python(dict(sorted(journal.items())), mode="json")
    JOURNAL_PATH.write_text(json.dumps(payload, indent=2))


def replay_fixed_rule(history: pd.DataFrame) -> dict[date, PaperSession]:
    """Every session of `history` after the first WARMUP_DAYS, as the fixed rule would have traded it."""
    first_session = history.index[0].date() + timedelta(days=SETTINGS.FIXED_RULE.WARMUP_DAYS)
    sessions = {session for session in history.index.date if session >= first_session}

    return _replay(fixed_rule_signal_bars(history), sessions)


def forward_summary() -> str:
    """Running total of the journal since FIXED_RULE.START."""
    sessions = [paper for session, paper in _read_journal().items() if session >= SETTINGS.FIXED_RULE.START]
    trades = sum(paper.trades for paper in sessions)
    wins = sum(paper.wins for paper in sessions)
    total_return = sum(paper.capital_return for paper in sessions)

    return (
        f"Fixed rule since {SETTINGS.FIXED_RULE.START} (simulated): {len(sessions)} sessions, {trades} trades, "
        f"{wins} profitable, capital return {round(100 * total_return, 2)}%"
    )


def paper_trade_session(session: date) -> PaperSession | None:
    """Replay the fixed rule on `session` from the 2m cache and record it in the journal (no orders).

    Run after the session's bars are cached. Re-running a session replaces its journal entry.
    """
    log.warning(f"TASK: Paper trade {SETTINGS.NAME} | {' | '.join(SETTINGS.FIXED_RULE.STRATEGY)} | {session}")

    start = pd.Timestamp(session - timedelta(days=SETTINGS.FIXED_RULE.WARMUP_DAYS))
    end = pd.Timestamp(session + timedelta(days=1))
    history = Storage().read()
    history = history[(history.index >= start) & (history.index < end)]
    if not (history.index.date == session).any():
        log.warning(f"No cached {SETTINGS.RESOLUTION} bars for {session}; nothing to paper trade")
        return None

    paper = _replay(fixed_rule_signal_bars(history), {session})[session]
    log.info(
        f"Paper session {session}: {paper.trades} trades, capital return {round(100 * paper.capital_return, 2)}%",
    )

    journal = _read_journal()
    journal[session] = paper
    _write_journal(journal)
    log.warning(forward_summary())

    return paper
