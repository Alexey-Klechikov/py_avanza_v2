import warnings
from datetime import date, timedelta

import pandas as pd

from config import SETTINGS
from services.storage.operators import Storage
from services.storage.windows import DataWindow
from tasks.backtest.model import train_weighted_model
from tasks.backtest.paper_trade import PaperSession, replay_fixed_rule
from tasks.backtest.weighted_walk_forward import weighted_walk_forward
from utils.constants import TODAY_MIDNIGHT
from utils.logger.operators import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.set_option("display.max_rows", None)


set_handlers("development")
log = get_logger()


def _log_sessions(title: str, sessions: dict[date, PaperSession]) -> None:
    """Per-quarter trades, profitable trades and capital return of replayed sessions, then the total."""
    table = pd.DataFrame(
        [(session, paper.trades, paper.wins, paper.capital_return) for session, paper in sessions.items()],
        columns=["session", "trades", "wins", "capital_return"],
    )
    quarters = table.groupby(pd.PeriodIndex(table["session"], freq="Q"))[["trades", "wins", "capital_return"]]
    log.info("\n" + quarters.sum().round(3).to_string())
    log.warning(
        f"{title}: {len(table)} sessions, {table['trades'].sum()} trades, {table['wins'].sum()} profitable, "
        f"capital return {round(100 * table['capital_return'].sum(), 2)}%",
    )


def run_fixed_rule_replay(period_days: int):
    """Replay SETTINGS.FIXED_RULE over the last `period_days` of the cache (no files written)."""
    window = DataWindow.days_before(TODAY_MIDNIGHT + timedelta(days=1), period_days)
    log.warning(f"Fixed rule replay: {' | '.join(SETTINGS.FIXED_RULE.STRATEGY)} over {window}")

    _log_sessions("Fixed rule", replay_fixed_rule(window.slice(Storage().read())))


def run_weighted_walk_forward(test_sessions: int, refit_sessions: int = 5):
    """Refit the weighted score every `refit_sessions` sessions on the data before, trade the next ones with those
    weights (no files written), and log the out-of-sample result."""
    walk_forward = weighted_walk_forward(
        Storage().read(),
        Storage(resolution="1d").read(),
        test_sessions=test_sessions,
        refit_sessions=refit_sessions,
    )
    _log_sessions("Weighted walk-forward", walk_forward.sessions)

    correlations = pd.Series(walk_forward.correlations)
    log.warning(
        f"Score vs move correlation {correlations.mean():+.4f} "
        f"(t {correlations.mean() / correlations.std() * len(correlations) ** 0.5:+.2f}), "
        f"votes kept median {int(pd.Series(walk_forward.kept_votes).median())}",
    )


if __name__ == "__main__":
    # "weighted_walk_forward" (no files written), "weighted_training" (writes the weighted model file), "fixed_rule"
    mode = "weighted_walk_forward"

    if mode == "weighted_walk_forward":
        run_weighted_walk_forward(test_sessions=500)

    elif mode == "weighted_training":
        train_weighted_model(Storage().read(), Storage(resolution="1d").read())

    elif mode == "fixed_rule":
        run_fixed_rule_replay(period_days=1000)
