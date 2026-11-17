import warnings
from datetime import timedelta

import pandas as pd
from pathos.multiprocessing import ProcessingPool as Pool

from config import SETTINGS
from services.ta.figure import Figure
from services.ta.indicators.models.indicator import Indicator, Panel, Plot, Plots
from services.ta.operators import get_indicators, get_strategies, read_top_strategies
from services.ta.strategies.models.strategy import ComposeStrategiesListMethod, Strategy
from services.ta.strategies.operators import dump_strategies_in_file
from services.ta.strategies.signals import SIGNAL_COLUMNS, mark_strategy_signals
from tasks.backtest.live_replay import replay_live_selection
from tasks.backtest.selection import select_daily_strategies, select_training_strategies
from tasks.backtest.simulator import simulate_strategy
from utils.logger.operators import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)


log = get_logger()


SIGNAL_PLOT_COLORS = {"LONG": "green", "SHORT": "red", "EXIT": "black"}


def _simulate_all(data: pd.DataFrame, strategies: list[Strategy]) -> list[Strategy]:
    progress_labels = [f" {number} / {len(strategies)}" for number in range(1, len(strategies) + 1)]

    with Pool() as pool:
        return list(pool.map(simulate_strategy, [data] * len(strategies), strategies, progress_labels))


def _select_for_today(strategies: list[Strategy], data: pd.DataFrame) -> list[Strategy]:
    # The live loop only trades strategies with MIN_EFFICIENCY win share: keep the file to exactly those, so an
    # empty selection (and its warning) means the bot really sits out
    tradable = [
        strategy
        for strategy in strategies
        if strategy.trade_stats.profitable_share >= SETTINGS.STRATEGY.MIN_EFFICIENCY
    ]
    scored_strategies = select_daily_strategies(tradable, as_of=data.index[-1].date() + timedelta(days=1))

    for scored_strategy in scored_strategies:
        log.info(
            f"Expected edge {round(scored_strategy.expected_edge * 100, 3)}% per trade: {scored_strategy.strategy.name}"
        )

    if not scored_strategies:
        log.warning("No strategy clears STRATEGY.MIN_EDGE; writing an empty strategies file, no trading until it does")

    return [scored_strategy.strategy for scored_strategy in scored_strategies]


def _log_performance(strategies: list[Strategy]) -> None:
    for strategy in strategies:
        stats = strategy.trade_stats
        log.info(
            f"{strategy.name}. Trades: {stats.total_trades}. Profit: {round(stats.total_profit, 2)}. "
            f"Profitable trades: {round(100 * stats.profitable_share)}%",
        )


def _log_live_selection_replay(
    data: pd.DataFrame,
    indicators_mapping: dict[str, dict[str, Indicator]],
    strategies_file_name_suffix: str | None,
) -> None:
    live_strategies = read_top_strategies(
        indicators_mapping,
        SETTINGS.NAME,
        filter_by_min_efficiency=SETTINGS.STRATEGY.MIN_EFFICIENCY,
        limit_count=SETTINGS.STRATEGY.COUNT_MAX,
        strategies_file_name_suffix=strategies_file_name_suffix,
    )
    stats = replay_live_selection(data, live_strategies)

    log.warning(
        f"Live selection replay of {len(live_strategies)} strategies. Trades: {stats.total_trades}. "
        f"Profit: {round(stats.total_profit, 2)}. Profitable trades: {round(100 * stats.profitable_share)}%",
    )


def _plot_signals(data: pd.DataFrame, strategy: Strategy) -> None:
    mark_strategy_signals(data, strategy)

    figure = Figure(data=data)
    for indicator in strategy.indicators_logic:
        figure.add_plot(indicator.plots)

    figure.add_plot(
        Plots(
            panel=Panel.MAIN,
            list=[
                Plot(columns=[column], type="scatter", color=SIGNAL_PLOT_COLORS[column], markersize=50)
                for column in SIGNAL_COLUMNS
                if not data[column].isnull().all()
            ],
        ),
    )
    figure.show()


# MAIN
def backtest_trade_strategies(
    data: pd.DataFrame,
    compose_strategies_list_method: ComposeStrategiesListMethod,
    indicators_filter: list[str] | None = None,
    strategies_file_name_suffix_old: str | None = None,
    strategies_file_name_suffix_new: str | None = None,
    plot: bool = False,
    **kwargs,
) -> list[Strategy]:
    """Simulate the composed strategies on `data`, select, and write the strategies file.

    GENERATE and EXTEND are training levels (select_training_strategies). READ is the final test: it keeps the
    strategies whose expected edge clears MIN_EDGE (select_daily_strategies) and logs a replay of the live
    selection over the same data.
    """
    indicators_mapping = get_indicators(data, **kwargs)

    strategies = get_strategies(
        compose_strategies_list_method,
        indicators_mapping,
        SETTINGS.NAME,
        strategies_file_name_suffix_old,
    )

    if indicators_filter:
        strategies = [
            strategy for strategy in strategies if any(indicator in strategy.name for indicator in indicators_filter)
        ]

    strategies = _simulate_all(data, strategies)

    if plot:
        for strategy in strategies:
            _plot_signals(data, strategy)

    is_final_test = compose_strategies_list_method == ComposeStrategiesListMethod.READ
    if is_final_test:
        strategies = _select_for_today(strategies, data)
    else:
        strategies = select_training_strategies(strategies, min_trades=SETTINGS.STRATEGY.MIN_TRADES_TRAIN)

    _log_performance(strategies)
    dump_strategies_in_file(strategies, SETTINGS.NAME, strategies_file_name_suffix_new)

    if is_final_test:
        _log_live_selection_replay(data, indicators_mapping, strategies_file_name_suffix_new)

    return strategies
