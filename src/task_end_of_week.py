import warnings
from datetime import datetime, time, timedelta

import pandas as pd

from apis.telegram.operators import Telegram
from backtest import backtest_hold_interday, backtest_hold_intraday, backtest_strategies
from config import SETTINGS_HOLD_OMX_DT, SETTINGS_TRADE_OMX
from services.hold.models import Direction, Scope
from services.hold.operators import Backlog
from services.storage import Storage
from services.ta.strategies.models import ComposeStrategiesListMethod
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.simplefilter(action="ignore", category=UserWarning)

set_handlers("end_of_week")
log = get_logger()


def generate_strategies(settings) -> None:
    period_days = 40

    data = Storage(settings).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    log.warning(f"Generating strategies for {settings.NAME} ({settings.RESOLUTION}, {period_days} days)")
    backtest_strategies(
        data,
        ComposeStrategiesListMethod.GENERATE,
        settings,
        old_strategies_file_name=None,
        new_strategies_file_name="strategies_dev_3.json",
        plot=False,
    )

    for i in range(3, settings.TRADING_STRATEGY_INDICATORS):
        log.warning(
            f"Extending strategies ({i} -> {i + 1}) for {settings.NAME} ({settings.RESOLUTION}, {period_days} days)",
        )
        backtest_strategies(
            data,
            ComposeStrategiesListMethod.EXTEND,
            settings,
            old_strategies_file_name=f"strategies_dev_{i}.json",
            new_strategies_file_name=f"strategies_dev_{i + 1}.json",
            plot=False,
        )

    period_days = 60

    data = Storage(settings).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    log.warning(f"Backtesting strategies for {settings.NAME} ({settings.RESOLUTION}, {period_days} days)")
    backtest_strategies(
        data,
        ComposeStrategiesListMethod.READ,
        settings,
        old_strategies_file_name=f"strategies_dev_{settings.TRADING_STRATEGY_INDICATORS}.json",
        new_strategies_file_name="strategies.json",
        plot=False,
    )


def generate_hold_rules_intraday(settings) -> None:
    period_days = 40

    start = time(10, 0)
    end = time(16, 50)

    log.warning(
        f"Generating INTRADAY hold rules using period {period_days} days "
        + f"with buy/sell time between {start} and {end}",
    )

    times = [i.time() for i in pd.date_range(start=start.strftime("%H:%M"), end=end.strftime("%H:%M"), freq="4min")]
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
        )

        backlog.rules += hold_rules_per_direction

    for hold_rule in backlog.rules:
        log.info(f"Hold Rule: {hold_rule.dump_dict()}")

    backlog.write_rules(settings, Scope.INTRADAY)


def generate_hold_rules_interday(settings) -> None:
    period_days = 40

    eod = time(16, 50)
    close = time(10, 00)
    direction = Direction.BULL

    log.warning(
        f"Generating INTERDAY hold rules for direction {direction.value} "
        + f"using period {period_days} days with eod/close time between {eod} and {close}",
    )

    data = Storage(settings).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    backlog = Backlog()

    hold_rule = backtest_hold_interday(data, eod, close, direction, settings.REF_PRICE)

    log.info(f"Hold Rule: {hold_rule.dump_dict()}")

    backlog.rules.append(hold_rule)
    backlog.write_rules(settings, Scope.INTERDAY)


if __name__ == "__main__":
    try:
        generate_strategies(SETTINGS_TRADE_OMX)
        generate_hold_rules_intraday(SETTINGS_HOLD_OMX_DT)
        generate_hold_rules_interday(SETTINGS_HOLD_OMX_DT)

    except Exception as e:
        telegram = Telegram()
        telegram.messages = ["Error in task_eow.py"]
        telegram.send_message()

        raise e
