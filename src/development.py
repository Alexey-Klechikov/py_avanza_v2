import json
import os
import warnings
from datetime import timedelta

import pandas as pd

from config import (
    SETTINGS_HOLD_CORRELATION,
    SETTINGS_HOLD_STATISTICS,
    SETTINGS_TRADE_CANDLESTICKS,
    SETTINGS_TRADE_LEVELS,
    SETTINGS_TRADE_STRATEGIES,
)
from services import Storage
from services.ta.strategies.models import ComposeStrategiesListMethod
from tasks.hold_correlation import (
    BacklogHoldCorrelation,
    backtest_hold_interday_correlation,
    backtest_hold_intraday_correlation,
)
from tasks.hold_statistics import (
    BacklogHoldStatistics,
    backtest_hold_interday_statistics,
    backtest_hold_intraday_statistics,
)
from tasks.hold_statistics.models import Direction, Scope
from tasks.trade_candlesticks import BacklogTradeCandlesticks, backtest_trade_candlesticks
from tasks.trade_levels import backtest_trade_levels
from tasks.trade_strategies import backtest_trade_strategies
from utils.constants import TODAY_MIDNIGHT
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.set_option("display.max_rows", None)


set_handlers("development")
log = get_logger()


def _get_data(period_days: int, settings, resolution: str | None = None):
    data = Storage(settings, resolution).read()
    data = data.loc[(data.index >= TODAY_MIDNIGHT - timedelta(days=period_days)) & (data.index < TODAY_MIDNIGHT)]
    data.index = pd.to_datetime(data.index)

    return data


# Trade strategies


def run_strategies_generation(settings, period_days: int, full: bool, comment: str | None = None):
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
    new_strategies_file_name_suffix = f"dev_6_{'-'.join(indicator_to_test)}_"

    for length in [i for i in range(16, 30, 2)]:
        kwargs = {"fast": 14, "slow": 30, "signal": length, "mamode": "dema", "length_divergence": 28}
        settings.INDICATORS[indicator_to_test[0]][indicator_to_test[1]] = kwargs

        log.warning(f"Testing for {indicator_to_test}_{list(kwargs.items())}")
        backtest_trade_strategies(
            _get_data(period_days, settings),
            ComposeStrategiesListMethod.EXTEND,
            settings,
            old_strategies_file_name="dev_5",
            new_strategies_file_name=new_strategies_file_name_suffix
            + f"{'_'.join([f'{k}={v}' for k, v in kwargs.items()])}",
            indicators_filter=[indicator_to_test[1]],
            **kwargs,
        )

    stats = []
    for file in os.listdir("src/config"):
        if new_strategies_file_name_suffix not in file:
            continue

        strategies = json.load(open(f"src/config/{file}"))
        if not strategies:
            continue

        s = strategies[0]

        stats.append(
            (
                file.replace(new_strategies_file_name_suffix, "").replace(".json", ""),
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


# Trade candlesticks


def run_trade_candlesticks_rules_generation(settings, period_days: int):
    data = _get_data(period_days, settings)

    candlestick_patterns = backtest_trade_candlesticks(data)

    backlog = BacklogTradeCandlesticks()
    backlog.rules = candlestick_patterns
    backlog.write_rules(settings.REF_PRICE)


# Hold statistics


def run_hold_interday_statistics_rules_generation(settings, period_days: int, slice_duration: int, direction: Direction):
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


def run_hold_intraday_statistics_rules_generation(settings, period_days: int, slice_duration: int):
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


# Hold correlation


def run_hold_intraday_correlation_rules_generation(settings, period_days: int, slice_duration: int):
    backlog = BacklogHoldCorrelation()
    hold_rules = backtest_hold_intraday_correlation(
        settings,
        _get_data(period_days, settings, resolution="5m"),
        slice_duration,
    )
    for i, hold_rule in enumerate(hold_rules):
        log.info(f"Hold Rule {i+1}: {hold_rule.dump_dict()}")

    backlog.rules = hold_rules
    backlog.write_rules(scope=Scope.INTRADAY)  # type: ignore


def run_hold_interday_correlation_rules_generation(settings, period_days: int, slice_duration: int):
    backlog = BacklogHoldCorrelation()
    hold_rules = backtest_hold_interday_correlation(
        settings,
        _get_data(period_days, settings, resolution="5m"),
        slice_duration,
    )
    for i, hold_rule in enumerate(hold_rules):
        log.info(f"Hold Rule {i+1}: {hold_rule.dump_dict()}")

    backlog.rules = hold_rules
    backlog.write_rules(scope=Scope.INTERDAY)  # type: ignore


# Trade levels


def run_trade_levels_backtest(settings, period_days: int):
    data = _get_data(period_days, settings)

    backtest_trade_levels(data, settings)


if __name__ == "__main__":
    settings = SETTINGS_TRADE_STRATEGIES
    run_strategies_generation(settings, period_days=40, full=True)
    # run_test_for_selected_indicators(settings, period_days=60)
    # run_plotting_for_active_strategies(settings, period_days=5)

    settings = SETTINGS_HOLD_STATISTICS
    # run_hold_intraday_statistics_rules_generation(settings, period_days=40, slice_duration=4)
    # run_hold_interday_statistics_rules_generation(settings, period_days=40, slice_duration=2, direction=Direction.BULL)

    settings = SETTINGS_HOLD_CORRELATION
    # run_hold_intraday_correlation_rules_generation(settings, period_days=40, slice_duration=10)
    # run_hold_interday_correlation_rules_generation(settings, period_days=40, slice_duration=10)

    settings = SETTINGS_TRADE_CANDLESTICKS
    # run_trade_candlesticks_rules_generation(settings, period_days=60)

    settings = SETTINGS_TRADE_LEVELS
    # run_trade_levels_backtest(settings, period_days=20)
