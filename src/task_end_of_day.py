import platform
import warnings
from datetime import timedelta

import pandas as pd
from avanza.constants import Resolution, TimePeriod

from apis.avanza.operators import Chart
from apis.investing.client.models import Resolution as InvestingResolution
from apis.investing.operators import Ticker as InvestingTicker
from apis.telegram.operators import Telegram
from apis.yahoo.client.models import Interval, Period
from apis.yahoo.operators import Ticker as YahooTicker
from config import SETTINGS_HOLD_STATISTICS, SETTINGS_TRADE_CANDLESTICKS, SETTINGS_TRADE_STRATEGIES
from hold_correlation import (
    BacklogHoldCorrelation,
    backtest_hold_interday_correlation,
    backtest_hold_intraday_correlation,
)
from hold_statistics import BacklogHoldStatistics, backtest_hold_interday_statistics, backtest_hold_intraday_statistics
from hold_statistics.models import Direction, Scope
from services import Storage
from services.ta.strategies.models import ComposeStrategiesListMethod
from trade_candlesticks import BacklogTradeCandlesticks, backtest_trade_candlesticks
from trade_strategies import backtest_trade_strategies as _backtest_trade_strategies
from utils.constants import TODAY_MIDNIGHT
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)

set_handlers("end_of_day")
log = get_logger()


def _get_data(period_days: int, settings, resolution: str | None = None):
    data = Storage(settings, resolution).read()
    data = data.loc[(data.index >= TODAY_MIDNIGHT - timedelta(days=period_days)) & (data.index < TODAY_MIDNIGHT)]
    data.index = pd.to_datetime(data.index)

    return data


def cache_history(settings):
    log.warning(f"TASK: Cache {settings.NAME} data")

    for resolution_ava, resolution_investing, interval_yahoo in [
        (Resolution.MINUTE, InvestingResolution.ONE_MINUTE, Interval.ONE_MINUTE),
        (Resolution.TWO_MINUTES, None, Interval.TWO_MINUTES),
        (Resolution.FIVE_MINUTES, InvestingResolution.FIVE_MINUTES, Interval.FIVE_MINUTES),
        (Resolution.HOUR, InvestingResolution.SIXTY_MINUTES, Interval.SIXTY_MINUTES),
    ]:
        storage = Storage(settings, resolution=interval_yahoo.value.raw)
        rows_before = storage.read().shape[0]

        if settings.TRADING_DATA == "avanza":
            data_ava = Chart.get_chart_data(settings, TimePeriod.TODAY, resolution_ava)
            storage.write(data_ava)

        elif settings.TRADING_DATA == "yahoo":
            data_yahoo = YahooTicker(settings).get_history(period=Period.FIVE_DAYS, interval=interval_yahoo)
            storage.write(data_yahoo)

        if False and resolution_investing and platform.system() == "Darwin":
            for i in range(5, 60, 5):
                data_investing = InvestingTicker(settings).get_history(
                    resolution=resolution_investing,
                    period_days=i,
                )
                storage.write(data_investing)

        rows_after = storage.read().shape[0]
        log.info(f"Cached ({interval_yahoo.value.raw}): {rows_before} rows before -> {rows_after} rows after")


def backtest_trade_strategies(settings, period_days: int):
    log.warning(f"TASK: Backtest strategies on {settings.NAME} | {settings.RESOLUTION} | {period_days} days")

    _backtest_trade_strategies(
        _get_data(period_days, settings),
        ComposeStrategiesListMethod.READ,
        settings,
        old_strategies_file_name=f"dev_{settings.TRADING_STRATEGY_INDICATORS}",
    )


def generate_hold_rules_intraday_statistics(settings, period_days: int, slice_duration: int) -> None:
    log.warning(
        f"TASK: Generate INTRADAY statistics hold rules using period {period_days} days "
        + f"and slice_duration {slice_duration} mins.",
    )

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


def generate_hold_rules_interday_statistics(
    settings,
    period_days: int,
    slice_duration: int,
    direction: Direction,
) -> None:
    log.warning(
        f"TASK: Generate INTERDAY statistics hold rules for direction {direction.value} "
        + f"using period {period_days} days and slice_duration {slice_duration} mins.",
    )

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


def generate_hold_rules_intraday_correlation(settings, period_days: int, slice_duration: int):
    log.warning(
        f"TASK: Generate INTRADAY correlation hold rules using period {period_days} days "
        + f"and slice_duration {slice_duration} mins.",
    )

    hold_rules = backtest_hold_intraday_correlation(
        settings,
        _get_data(period_days, settings, resolution="5m"),
        slice_duration,
    )
    for i, hold_rule in enumerate(hold_rules):
        log.info(f"Hold Rule {i+1}: {hold_rule.dump_dict()}")

    backlog = BacklogHoldCorrelation()
    backlog.rules = hold_rules
    backlog.write_rules(scope=Scope.INTRADAY)  # type: ignore


def generate_hold_rules_interday_correlation(settings, period_days: int, slice_duration: int):
    log.warning(
        f"TASK: Generate INTERDAY correlation hold rules using period {period_days} days "
        + f"and slice_duration {slice_duration} mins.",
    )

    hold_rules = backtest_hold_interday_correlation(
        settings,
        _get_data(period_days, settings, resolution="5m"),
        slice_duration,
    )
    for i, hold_rule in enumerate(hold_rules):
        log.info(f"Hold Rule {i+1}: {hold_rule.dump_dict()}")

    backlog = BacklogHoldCorrelation()
    backlog.rules = hold_rules
    backlog.write_rules(scope=Scope.INTERDAY)  # type: ignore


def generate_candlestick_patterns_rules(settings, period_days: int) -> None:
    log.warning(f"Generating candlesticks rules for {settings.NAME} ({settings.RESOLUTION}, {period_days} days)")

    candlestick_patterns = backtest_trade_candlesticks(_get_data(period_days, settings))

    backlog = BacklogTradeCandlesticks()
    backlog.rules = candlestick_patterns
    backlog.write_rules(settings.REF_PRICE)


if __name__ == "__main__":
    try:
        cache_history(SETTINGS_TRADE_STRATEGIES)
        backtest_trade_strategies(SETTINGS_TRADE_STRATEGIES, period_days=40)
        generate_hold_rules_intraday_statistics(SETTINGS_HOLD_STATISTICS, period_days=40, slice_duration=4)
        generate_hold_rules_interday_statistics(
            SETTINGS_HOLD_STATISTICS,
            period_days=40,
            slice_duration=2,
            direction=Direction.BULL,
        )
        generate_candlestick_patterns_rules(SETTINGS_TRADE_CANDLESTICKS, period_days=60)

        # generate_hold_rules_intraday_correlation(SETTINGS_HOLD_CORRELATION, period_days=40, slice_duration=10)
        # generate_hold_rules_interday_correlation(SETTINGS_HOLD_CORRELATION, period_days=40, slice_duration=10)

    except Exception as e:
        telegram = Telegram()
        telegram.messages = ["Error in task_eod.py"]
        telegram.send_message()

        raise e
