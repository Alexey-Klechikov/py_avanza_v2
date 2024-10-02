import json
import os
import warnings
from datetime import datetime, time, timedelta
from pprint import pprint

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


def run_full_strategies_generation(settings):
    period_days = 60

    data = Storage(settings).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
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

    period_days = 60

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
        new_strategies_file_name="strategies.json",
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


def test_hold_interday(settings):
    period_days = 60

    eod = time(16, 50)
    close = time(10, 00)
    direction = Direction.BULL

    omx_reference_price = 2600

    data = Storage(settings).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    result = backtest_hold_interday(data, eod, close, direction, omx_reference_price)

    pprint(result)


def test_hold_intraday(settings):
    period_days = 60

    start = time(10, 0)
    end = time(17, 0)

    omx_reference_price = 2600

    times = [i.time() for i in pd.date_range(start=start.strftime("%H:%M"), end=end.strftime("%H:%M"), freq="10min")]
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
            omx_reference_price,
        )

        backlog.rules += hold_rules_per_direction

    for hold_rule in backlog.rules:
        log.debug(f"Hold Rule: {hold_rule.dump_dict()}")

    backlog.write_rules(settings, Scope.INTRADAY)


if __name__ == "__main__":
    settings = SETTINGS_TRADE_OMX
    # run_full_strategies_generation(settings)
    # run_test_for_selected_indicators(settings)
    # run_plotting_for_active_strategies(settings)

    settings = SETTINGS_HOLD_OMX_DT  # SETTINGS_HOLD_OMX_MAIN
    # test_hold_interday(settings)
    test_hold_intraday(settings)
