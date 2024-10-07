import json
import os
import warnings
from datetime import datetime, timedelta

import pandas as pd

from backtest import backtest_hold_interday, backtest_hold_intraday, backtest_strategies
from config import SETTINGS_HOLD_OMX_DT, SETTINGS_TRADE_OMX
from services.hold.models import Direction, Scope
from services.hold.operators import Backlog
from services.storage import Storage
from services.ta.strategies.models import ComposeStrategiesListMethod
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)


set_handlers("development")
log = get_logger()


def run_strategies_generation(settings, period_days, full, comment: str = ""):
    if full:
        data = Storage(settings).read()
        data = data.loc[
            data.index
            >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days + 20)
        ]

        log.warning("Generating strategies")
        backtest_strategies(
            data,
            ComposeStrategiesListMethod.GENERATE,
            settings,
            old_strategies_file_name=None,
            new_strategies_file_name="strategies_dev_3.json",
            indicators_filter=[],
            plot=False,
        )

        for i in range(3, settings.TRADING_STRATEGY_INDICATORS):
            log.warning(f"Extending strategies ({i} -> {i + 1})")
            backtest_strategies(
                data,
                ComposeStrategiesListMethod.EXTEND,
                settings,
                old_strategies_file_name=f"strategies_dev_{i}.json",
                new_strategies_file_name=f"strategies_dev_{i + 1}.json",
                indicators_filter=[],
                plot=False,
            )

    data = Storage(settings).read()
    data = data.loc[
        (data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days))
        & (data.index < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
    ]

    log.warning("Backtesting strategies")
    backtest_strategies(
        data,
        ComposeStrategiesListMethod.READ,
        settings,
        old_strategies_file_name=f"strategies_dev_{settings.TRADING_STRATEGY_INDICATORS}.json",
        new_strategies_file_name="strategies.json" if not comment else f"strategies_{comment}.json",
        indicators_filter=[],
        plot=False,
    )


def run_plotting_for_active_strategies(settings):
    period_days = 5

    data = Storage(settings).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    backtest_strategies(
        data.copy(),
        ComposeStrategiesListMethod.READ,
        settings,
        old_strategies_file_name="strategies.json",
        new_strategies_file_name=None,
        indicators_filter=[],
        plot=True,
    )


def run_test_for_selected_indicators(settings):
    period_days = 60

    data = Storage(settings).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    indicator_to_test = ("Momentum", "STC")
    new_strategies_file_name_prefix = f"strategies_dev_6_{'-'.join(indicator_to_test)}_"

    for tclength, fast, slow in [(14, 22, i) for i in range(35, 55, 2)]:
        kwargs = {"tclength": tclength, "fast": fast, "slow": slow, "factor": 0.55}
        settings.INDICATORS[indicator_to_test[0]][indicator_to_test[1]] = kwargs

        log.warning(f"Testing for {indicator_to_test}_{list(kwargs.items())}")
        backtest_strategies(
            data.copy(),
            ComposeStrategiesListMethod.EXTEND,
            settings,
            old_strategies_file_name="strategies_dev_5.json",
            new_strategies_file_name=new_strategies_file_name_prefix
            + f"{'_'.join([f'{k}={v}' for k, v in kwargs.items()])}.json",
            indicators_filter=[indicator_to_test[1]],
            plot=False,
            **kwargs,
        )

    new_strategies_file_name_prefix = f"{settings.FILE_PREFIX}_{new_strategies_file_name_prefix}"

    stats = []
    for file in os.listdir("src/config"):
        if not file.startswith(new_strategies_file_name_prefix):
            continue

        strategies = json.load(open(f"src/config/{file}"))
        if not strategies:
            continue

        s = strategies[0]
        stats.append(
            (
                file.replace(new_strategies_file_name_prefix, "").replace(".json", ""),
                round(s["profitable_trades_share"] * s["total_profit"], 2),
                s["profitable_trades_share"],
                s["total_profit"],
                s["name"],
                round(sum([i["profitable_trades_share"] for i in strategies])),
            ),
        )

    log.warning(f"Stats for {indicator_to_test}")
    for s in sorted(stats, key=lambda x: x[1], reverse=True):
        log.info("> " + " | ".join([str(i) for i in s]))


def test_hold_interday(settings, slice_duration):
    period_days = 40

    eod_times = [i.time() for i in pd.date_range(start="16:50", end="17:16", freq=f"{slice_duration}min")]
    close_times = [i.time() for i in pd.date_range(start="09:02", end="10:00", freq=f"{slice_duration}min")]
    direction = Direction.BULL

    data = Storage(settings).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    hold_rule = backtest_hold_interday(data, eod_times, close_times, direction, settings.REF_PRICE)

    log.info(f"Hold Rule: {hold_rule.dump_dict()}")

    backlog = Backlog()
    backlog.rules.append(hold_rule)
    backlog.write_rules(settings, Scope.INTERDAY)


def test_hold_intraday(settings, slice_duration):
    period_days = 40

    times = [i.time() for i in pd.date_range(start="10:00", end="17:00", freq=f"{slice_duration}min")]
    buy_time_sell_time_combinations = [
        (buy_time, sell_time) for buy_time in times for sell_time in times if buy_time < sell_time
    ]

    data = Storage(settings).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]
    data.index = pd.to_datetime(data.index)

    backlog = Backlog()
    for direction in [Direction.BULL, Direction.BEAR]:
        hold_rules_per_direction = backtest_hold_intraday(
            data,
            buy_time_sell_time_combinations,
            direction,
            settings.REF_PRICE,
            slice_duration,
        )

        backlog.rules += hold_rules_per_direction

    for hold_rule in backlog.rules:
        log.info(f"Hold Rule: {hold_rule.dump_dict()}")

    backlog.write_rules(settings, Scope.INTRADAY)


if __name__ == "__main__":
    settings = SETTINGS_TRADE_OMX
    # run_strategies_generation(settings, period_days=40, full=False)
    # run_test_for_selected_indicators(settings)
    # run_plotting_for_active_strategies(settings)

    settings = SETTINGS_HOLD_OMX_DT
    # test_hold_intraday(settings, slice_duration=4)
    # test_hold_interday(settings, slice_duration=2)
