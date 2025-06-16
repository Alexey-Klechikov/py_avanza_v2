import warnings
from datetime import datetime, timedelta

import pandas as pd

from apis.avanza.operators.portfolio import Portfolio
from apis.telegram.operators import Telegram
from config import SETTINGS
from services.storage.operators import Storage
from services.ta.strategies.models.strategy import ComposeStrategiesListMethod
from tasks.trade_strategies.backtest import backtest_trade_strategies
from utils.constants import TODAY_MIDNIGHT
from utils.logger.operators import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.simplefilter(action="ignore", category=UserWarning)

set_handlers("end_of_week")
log = get_logger()


def _get_data(point_of_origin: datetime, period_days: int):
    log.info(f"Get data: {(point_of_origin - timedelta(days=period_days)).date()} - {point_of_origin.date()}")

    data = Storage().read()
    data = data.loc[(data.index >= point_of_origin - timedelta(days=period_days)) & (data.index < point_of_origin)]
    data.index = pd.to_datetime(data.index)

    return data


def generate_strategies(period_days_back_test: int, period_days_forward_test: int) -> None:
    log.warning(f"Back-test strategies for {SETTINGS.NAME} ({SETTINGS.RESOLUTION}, {period_days_back_test} days)")
    backtest_trade_strategies(
        _get_data(
            point_of_origin=(TODAY_MIDNIGHT - timedelta(days=period_days_forward_test)),
            period_days=period_days_back_test,
        ),
        ComposeStrategiesListMethod.GENERATE,
        strategies_file_name_suffix_new="dev_3",
    )

    for i in range(3, SETTINGS.STRATEGY.INDICATORS):
        log.warning(
            "Back-test strategies ({} -> {}) for {} ({}, {} days)".format(
                i,
                i + 1,
                SETTINGS.NAME,
                SETTINGS.RESOLUTION,
                period_days_back_test,
            ),
        )
        backtest_trade_strategies(
            _get_data(
                point_of_origin=(TODAY_MIDNIGHT - timedelta(days=period_days_forward_test)),
                period_days=period_days_back_test,
            ),
            ComposeStrategiesListMethod.EXTEND,
            strategies_file_name_suffix_old=f"dev_{i}",
            strategies_file_name_suffix_new=f"dev_{i + 1}",
        )

    log.warning(f"Forward-test strategies for {SETTINGS.NAME} ({SETTINGS.RESOLUTION}, {period_days_forward_test} days)")
    backtest_trade_strategies(
        _get_data(
            point_of_origin=TODAY_MIDNIGHT,
            period_days=period_days_forward_test,
        ),
        ComposeStrategiesListMethod.READ,
        strategies_file_name_suffix_old=f"dev_{SETTINGS.STRATEGY.INDICATORS}",
    )


if __name__ == "__main__":
    try:
        generate_strategies(period_days_back_test=90, period_days_forward_test=30)

        portfolio = Portfolio()
        portfolio.reload_balance()
        log.info(f"Portfolio balance: {portfolio.total_value}")
        log.info("------------")

    except Exception as e:
        telegram = Telegram()
        telegram.messages = ["Error in task_eow.py"]
        telegram.send_message()

        raise e
