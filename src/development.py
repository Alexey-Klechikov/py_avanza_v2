import os
import warnings
from datetime import date

import numpy as np
import pandas as pd

from services.storage.operators import Storage
from tasks.backtest.indicator_tuning import IndicatorGrid, tune_indicator
from tasks.backtest.paper_trade import PaperSession
from tasks.backtest.weighted_walk_forward import weighted_walk_forward
from tasks.shared.bars import bar_index
from tasks.shared.weighted_model import train_weighted_model
from utils.logger.operators import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.set_option("display.max_rows", None)
pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 120)

log = get_logger()

# Indicator tuning only sees data before this day; "weighted_holdout" then judges the chosen parameters once on the
# rest. Re-judging after every tweak turns the holdout into calibration data.
HOLDOUT_START = date(2025, 11, 19)
# Processes for the tuning candidates and the walk-forward refit periods; each holds its own copy of the history
# and builds vote frames of tens of MB, hence the cap
WORKERS = min(os.cpu_count() or 1, 8)


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


def run_weighted_walk_forward(test_sessions: int, refit_sessions: int = 5):
    """Refit the weighted score every `refit_sessions` sessions on the data before, trade the next ones with those
    weights (no files written), and log the out-of-sample result."""
    walk_forward = weighted_walk_forward(
        Storage().read(),
        Storage(resolution="1d").read(),
        test_sessions=test_sessions,
        refit_sessions=refit_sessions,
        workers=WORKERS,
    )
    _log_sessions("Weighted walk-forward", walk_forward.sessions)

    correlations = pd.Series(walk_forward.correlations)
    log.warning(
        f"Score vs move correlation {correlations.mean():+.4f} "
        f"(t {correlations.mean() / correlations.std() * len(correlations) ** 0.5:+.2f}), "
        f"votes kept median {int(pd.Series(walk_forward.kept_votes).median())}",
    )


def run_indicator_tuning(grid: IndicatorGrid, refit_sessions: int = 5):
    """Score every parameter set of `grid` (plus the current one and the indicator off) by the weighted score's
    walk-forward on the data before HOLDOUT_START; no files written. Copy the winner into SETTINGS.INDICATORS."""
    history = Storage().read()
    calibration = history.loc[history.index < pd.Timestamp(HOLDOUT_START)]
    log.warning(
        f"Tuning {grid.category}-{grid.name}: {len(grid.candidates())} candidates on "
        f"{calibration.index[0].date()} .. {calibration.index[-1].date()}",
    )

    results = tune_indicator(calibration, Storage(resolution="1d").read(), grid, refit_sessions, WORKERS)
    table = pd.DataFrame(
        {
            "params": [result.label or result.params for result in results],
            "edge": [round(result.edge, 2) for result in results],
            "correlation": [round(result.correlation, 4) for result in results],
            "periods > 0": [f"{result.positive_periods:.0%}" for result in results],
            "trades": [result.trades for result in results],
            "net per trade": [f"{100 * result.net_return_per_trade:+.2f}%" for result in results],
        },
    )
    log.warning(
        "Edge = t-statistic of the out-of-sample score/move correlation per refit period (higher is better; "
        "differences under ~1 are noise). Net per trade is after BACKTEST_SPREAD.\n" + table.to_string(index=False),
    )


def run_weighted_holdout(refit_sessions: int = 5):
    """The out-of-sample walk-forward on the sessions from HOLDOUT_START on: run once per chosen parameter set."""
    session_days = np.unique(bar_index(Storage().read()).date)
    run_weighted_walk_forward(test_sessions=int((session_days >= HOLDOUT_START).sum()), refit_sessions=refit_sessions)


if __name__ == "__main__":
    # Under the guard: worker processes re-import this module and must not reopen (truncate) the log files
    set_handlers("development")

    # "indicator_tuning" (no files written), "weighted_holdout" (no files written), "weighted_walk_forward"
    # (no files written), "weighted_training" (writes the weighted model file)
    mode = "weighted_training"

    if mode == "indicator_tuning":
        # A list is searched, a scalar stays fixed; every combination runs (about 30 s each, WORKERS at a time)
        run_indicator_tuning(
            IndicatorGrid(
                category="Volume",
                name="CMF",
                params={"length": list(range(20, 40, 4)), "length_divergence": list(range(20, 40, 4))},
            ),
        )

    elif mode == "weighted_holdout":
        run_weighted_holdout()

    elif mode == "weighted_walk_forward":
        run_weighted_walk_forward(test_sessions=500)

    elif mode == "weighted_training":
        train_weighted_model(Storage().read(), Storage(resolution="1d").read())
