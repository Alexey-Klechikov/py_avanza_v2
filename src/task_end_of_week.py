import warnings
from datetime import timedelta

import pandas as pd

from apis.avanza.operators import Portfolio, Transactions
from apis.telegram.operators import Telegram
from config import (
    SETTINGS_HOLD_CORRELATION,
    SETTINGS_HOLD_STATISTICS,
    SETTINGS_TRADE_CANDLESTICKS,
    SETTINGS_TRADE_STRATEGIES,
)
from services import Storage
from services.ta.strategies.models import ComposeStrategiesListMethod
from trade_candlesticks import backtest_trade_candlesticks
from trade_strategies import backtest_trade_strategies
from utils.constants import TODAY_MIDNIGHT
from utils.logger import get_logger, reset_file_handlers, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.simplefilter(action="ignore", category=UserWarning)

set_handlers("end_of_week")
log = get_logger()


def _get_data(period_days: int, settings, resolution: str | None = None):
    data = Storage(settings, resolution).read()
    data = data.loc[(data.index >= TODAY_MIDNIGHT - timedelta(days=period_days)) & (data.index < TODAY_MIDNIGHT)]
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


def generate_candlestick_patterns_rules(settings, period_days: int) -> None:
    log.warning(f"Generating candlesticks rules for {settings.NAME} ({settings.RESOLUTION}, {period_days} days)")
    backtest_trade_candlesticks(_get_data(period_days, settings))


if __name__ == "__main__":
    try:
        generate_strategies(SETTINGS_TRADE_STRATEGIES, period_days=40)
        generate_candlestick_patterns_rules(SETTINGS_TRADE_CANDLESTICKS, period_days=50)

        reset_file_handlers("deals")
        for task_name, account_id in [
            ("hold_statistics", SETTINGS_HOLD_STATISTICS.ACCOUNT_ID),
            ("hold_correlation", SETTINGS_HOLD_CORRELATION.ACCOUNT_ID),
            ("trade_strategies", SETTINGS_TRADE_STRATEGIES.ACCOUNT_ID),
        ]:
            Transactions(account_id).log_deals(log_header=task_name)

            portfolio = Portfolio(account_id)
            portfolio.reload_balance()
            log.info(f"Portfolio balance: {portfolio.total_value}")
            log.info("------------")

    except Exception as e:
        telegram = Telegram()
        telegram.messages = ["Error in task_eow.py"]
        telegram.send_message()

        raise e
