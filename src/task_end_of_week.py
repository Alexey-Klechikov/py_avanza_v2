import warnings
from datetime import timedelta

import pandas as pd

from apis.avanza.operators.portfolio import Portfolio
from apis.avanza.operators.transactions import Transactions
from apis.telegram.operators import Telegram
from config import SETTINGS
from services import Storage
from services.ta.strategies.models import ComposeStrategiesListMethod
from tasks.trade_strategies.backtest import backtest_trade_strategies
from utils.constants import TODAY_MIDNIGHT
from utils.logger import get_logger, reset_file_handlers, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.simplefilter(action="ignore", category=UserWarning)

set_handlers("end_of_week")
log = get_logger()


def _get_data(period_days: int):
    data = Storage().read()
    data = data.loc[(data.index >= TODAY_MIDNIGHT - timedelta(days=period_days)) & (data.index < TODAY_MIDNIGHT)]
    data.index = pd.to_datetime(data.index)

    return data


def generate_strategies(period_days: int) -> None:
    log.warning(f"Generating strategies for {SETTINGS.NAME} ({SETTINGS.RESOLUTION}, {period_days + 20} days)")
    backtest_trade_strategies(
        _get_data(period_days + 20),
        ComposeStrategiesListMethod.GENERATE,
        strategies_file_name_suffix_new="dev_3",
    )

    for i in range(3, SETTINGS.STRATEGY.INDICATORS):
        log.warning(
            f"Extending strategies ({i} -> {i + 1}) for {SETTINGS.NAME} ({SETTINGS.RESOLUTION}, {period_days + 20} days)",
        )
        backtest_trade_strategies(
            _get_data(period_days + 20),
            ComposeStrategiesListMethod.EXTEND,
            strategies_file_name_suffix_old=f"dev_{i}",
            strategies_file_name_suffix_new=f"dev_{i + 1}",
        )

    log.warning(f"Backtesting strategies for {SETTINGS.NAME} ({SETTINGS.RESOLUTION}, {period_days} days)")
    backtest_trade_strategies(
        _get_data(period_days),
        ComposeStrategiesListMethod.READ,
        strategies_file_name_suffix_old=f"dev_{SETTINGS.STRATEGY.INDICATORS}",
    )


if __name__ == "__main__":
    try:
        generate_strategies(period_days=40)

        reset_file_handlers("deals_OMX")
        Transactions().log_deals(log_header="trade_OMX")

        portfolio = Portfolio()
        portfolio.reload_balance()
        log.info(f"Portfolio balance: {portfolio.total_value}")
        log.info("------------")

    except Exception as e:
        telegram = Telegram()
        telegram.messages = ["Error in task_eow.py"]
        telegram.send_message()

        raise e
