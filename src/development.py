import json
import os
import warnings
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from backtest import (
    backtest_hold_interday_statistics,
    backtest_hold_intraday_correlation,
    backtest_hold_intraday_statistics,
    backtest_trade_strategies,
)
from config import SETTINGS_HOLD_STATISTICS, SETTINGS_TRADE_STRATEGIES
from services import BacklogHoldCorrelation, BacklogHoldStatistics, Storage
from services.hold_statistics.models import Direction, Scope
from services.ta.strategies.models import ComposeStrategiesListMethod
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)


set_handlers("development")
log = get_logger()


def _get_data(period_days: int, settings, resolution: Optional[str] = None):
    data = Storage(settings, resolution).read()
    data = data.loc[
        (data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days))
        & (data.index < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
    ]
    data.index = pd.to_datetime(data.index)

    return data


def run_strategies_generation(settings, period_days: int, full: bool, comment: Optional[str] = None):
    if full:
        log.warning("Generating strategies")
        backtest_trade_strategies(
            _get_data(period_days + 20, settings),
            ComposeStrategiesListMethod.GENERATE,
            settings,
            new_strategies_file_name="dev_3",
        )

        for i in range(3, settings.TRADING_STRATEGY_INDICATORS):
            log.warning(f"Extending strategies ({i} -> {i + 1})")
            backtest_trade_strategies(
                _get_data(period_days + 20, settings),
                ComposeStrategiesListMethod.EXTEND,
                settings,
                old_strategies_file_name=f"dev_{i}",
                new_strategies_file_name=f"dev_{i + 1}",
            )

    log.warning("Backtesting strategies")
    backtest_trade_strategies(
        _get_data(period_days, settings),
        ComposeStrategiesListMethod.READ,
        settings,
        old_strategies_file_name=f"dev_{settings.TRADING_STRATEGY_INDICATORS}",
        new_strategies_file_name=comment,
    )


def run_plotting_for_active_strategies(settings, period_days: int):
    backtest_trade_strategies(
        _get_data(period_days, settings),
        ComposeStrategiesListMethod.READ,
        settings,
        plot=True,
    )


def run_test_for_selected_indicators(settings, period_days: int):
    indicator_to_test = ("Volume", "KVO")
    new_strategies_file_name_prefix = f"dev_6_{'-'.join(indicator_to_test)}_"

    for length_divergence in [i for i in range(8, 34, 2)]:
        kwargs = {"fast": 11, "slow": 35, "signal": 18, "mamode": "ema", "length_divergence": length_divergence}
        settings.INDICATORS[indicator_to_test[0]][indicator_to_test[1]] = kwargs

        log.warning(f"Testing for {indicator_to_test}_{list(kwargs.items())}")
        backtest_trade_strategies(
            _get_data(period_days, settings),
            ComposeStrategiesListMethod.EXTEND,
            settings,
            old_strategies_file_name="dev_5",
            new_strategies_file_name=new_strategies_file_name_prefix
            + f"{'_'.join([f'{k}={v}' for k, v in kwargs.items()])}",
            indicators_filter=[indicator_to_test[1]],
            **kwargs,
        )

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
                round(sum([i["profitable_trades_share"] for i in strategies]), 2),
            ),
        )

    log.warning(f"Stats for {indicator_to_test}")
    for s in sorted(stats, key=lambda x: x[1], reverse=True):
        log.info("> " + " | ".join([str(i) for i in s]))


def test_hold_interday_statistics(settings, period_days: int, slice_duration: int, direction: Direction):
    hold_rule = backtest_hold_interday_statistics(
        _get_data(period_days, settings),
        slice_duration,
        direction,
        settings.REF_PRICE,
    )

    log.info(f"Hold Rule: {hold_rule.dump_dict()}")

    backlog = BacklogHoldStatistics()
    backlog.rules.append(hold_rule)
    backlog.write_rules(Scope.INTERDAY)


def test_hold_intraday_statistics(settings, period_days: int, slice_duration: int):
    backlog = BacklogHoldStatistics()
    for direction in [Direction.BULL, Direction.BEAR]:
        hold_rules_per_direction = backtest_hold_intraday_statistics(
            _get_data(period_days, settings),
            slice_duration,
            direction,
            settings.REF_PRICE,
        )

        backlog.rules += hold_rules_per_direction

    for hold_rule in backlog.rules:
        log.info(f"Hold Rule: {hold_rule.dump_dict()}")

    backlog.write_rules(Scope.INTRADAY)


def test_hold_intraday_correlation(settings, period_days: int, slice_duration: int):
    backlog = BacklogHoldCorrelation()
    hold_rules = backtest_hold_intraday_correlation(
        _get_data(period_days, settings, resolution="5m"),
        slice_duration,
    )
    for i, hold_rule in enumerate(hold_rules):
        log.info(f"Hold Rule {i+1}: {hold_rule.dump_dict()}")

    backlog.rules = hold_rules
    backlog.write_rules()


if __name__ == "__main__":
    settings = SETTINGS_TRADE_STRATEGIES
    # run_strategies_generation(settings, period_days=40, full=True)
    # run_test_for_selected_indicators(settings, period_days=60)
    # run_plotting_for_active_strategies(settings, period_days=5)

    settings = SETTINGS_HOLD_STATISTICS
    # test_hold_intraday_statistics(settings, period_days=40, slice_duration=4)
    # test_hold_interday_statistics(settings, period_days=40, slice_duration=2, direction=Direction.BULL)
    test_hold_intraday_correlation(settings, period_days=40, slice_duration=10)
