import warnings
from datetime import timedelta

import pandas as pd

from apis.avanza.operators.portfolio import Portfolio
from apis.telegram.operators import Telegram
from config import SETTINGS
from services.storage.operators import Storage
from services.ta.strategies.models.strategy import ComposeStrategiesListMethod
from tasks.backtest import backtest_trade_strategies
from utils.constants import TODAY_MIDNIGHT
from utils.logger.operators import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.simplefilter(action="ignore", category=UserWarning)

set_handlers("end_of_week")
log = get_logger()


def _get_data(period_days: int):
    log.info(f"Get data: {(TODAY_MIDNIGHT - timedelta(days=period_days)).date()} - {TODAY_MIDNIGHT.date()}")

    data = Storage().read()
    data = data.loc[(data.index >= TODAY_MIDNIGHT - timedelta(days=period_days)) & (data.index < TODAY_MIDNIGHT)]
    data.index = pd.to_datetime(data.index)

    return data


def generate_strategies(period_days_long_test: int, period_days_final_test: int) -> None:
    log.warning(f"Long-test strategies for {SETTINGS.NAME} ({SETTINGS.RESOLUTION}, {period_days_long_test} days)")
    backtest_trade_strategies(
        _get_data(period_days=period_days_long_test),
        ComposeStrategiesListMethod.GENERATE,
        strategies_file_name_suffix_new="dev_3",
    )

    for i in range(3, SETTINGS.STRATEGY.INDICATORS):
        log.warning(
            "Long-test strategies ({} -> {}) for {} ({}, {} days)".format(
                i,
                i + 1,
                SETTINGS.NAME,
                SETTINGS.RESOLUTION,
                period_days_long_test,
            ),
        )
        backtest_trade_strategies(
            _get_data(period_days=period_days_long_test),
            ComposeStrategiesListMethod.EXTEND,
            strategies_file_name_suffix_old=f"dev_{i}",
            strategies_file_name_suffix_new=f"dev_{i + 1}",
        )

    log.warning(f"Final-test strategies for {SETTINGS.NAME} ({SETTINGS.RESOLUTION}, {period_days_final_test} days)")
    backtest_trade_strategies(
        _get_data(period_days=period_days_final_test),
        ComposeStrategiesListMethod.READ,
        strategies_file_name_suffix_old=f"dev_{SETTINGS.STRATEGY.INDICATORS}",
    )


if __name__ == "__main__":
    try:
        generate_strategies(period_days_long_test=90, period_days_final_test=60)

        portfolio = Portfolio()
        portfolio.reload_balance()
        log.info(f"Portfolio balance: {portfolio.total_value}")
        log.info("------------")

    except Exception as e:
        telegram = Telegram()
        telegram.messages = ["Error in task_eow.py"]
        telegram.send_message()

        raise e
