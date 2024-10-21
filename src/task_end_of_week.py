import warnings
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from apis.telegram.operators import Telegram
from backtest import backtest_trade_strategies
from config import SETTINGS_TRADE_STRATEGIES
from services import Storage
from services.ta.strategies.models import ComposeStrategiesListMethod
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.simplefilter(action="ignore", category=UserWarning)

set_handlers("end_of_week")
log = get_logger()


def _get_data(period_days: int, settings, resolution: Optional[str] = None):
    data = Storage(settings, resolution).read()
    data = data.loc[
        (data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days))
        & (data.index < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
    ]
    data.index = pd.to_datetime(data.index)

    return data


def generate_strategies(settings, period_days: int) -> None:
    log.warning(f"Generating strategies for {settings.NAME} ({settings.RESOLUTION}, {period_days} days)")
    backtest_trade_strategies(
        _get_data(period_days + 20, settings),
        ComposeStrategiesListMethod.GENERATE,
        settings,
        new_strategies_file_name="dev_3",
    )

    for i in range(3, settings.TRADING_STRATEGY_INDICATORS):
        log.warning(
            f"Extending strategies ({i} -> {i + 1}) for {settings.NAME} ({settings.RESOLUTION}, {period_days} days)",
        )
        backtest_trade_strategies(
            _get_data(period_days + 20, settings),
            ComposeStrategiesListMethod.EXTEND,
            settings,
            old_strategies_file_name=f"dev_{i}",
            new_strategies_file_name=f"dev_{i + 1}",
        )

    log.warning(f"Backtesting strategies for {settings.NAME} ({settings.RESOLUTION}, {period_days} days)")
    backtest_trade_strategies(
        _get_data(period_days, settings),
        ComposeStrategiesListMethod.READ,
        settings,
        old_strategies_file_name=f"dev_{settings.TRADING_STRATEGY_INDICATORS}",
    )


if __name__ == "__main__":
    try:
        generate_strategies(SETTINGS_TRADE_STRATEGIES, period_days=40)

    except Exception as e:
        telegram = Telegram()
        telegram.messages = ["Error in task_eow.py"]
        telegram.send_message()

        raise e
