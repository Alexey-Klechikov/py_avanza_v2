import warnings
from datetime import timedelta

import pandas as pd

from apis.avanza.operators import Portfolio, Transactions
from apis.telegram.operators import Telegram
from config import SETTINGS_TRADE_STRATEGIES_GULD, SETTINGS_TRADE_STRATEGIES_OMX
from services import Storage
from services.ta.strategies.models import ComposeStrategiesListMethod
from tasks.trade_strategies import backtest_trade_strategies
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
    log.warning(f"Generating strategies for {settings.NAME} ({settings.RESOLUTION}, {period_days + 20} days)")
    backtest_trade_strategies(
        _get_data(period_days + 20, settings),
        ComposeStrategiesListMethod.GENERATE,
        settings,
        strategies_file_name_suffix_new="dev_3",
    )

    for i in range(3, settings.TRADING_STRATEGY_INDICATORS):
        log.warning(
            f"Extending strategies ({i} -> {i + 1}) for {settings.NAME} ({settings.RESOLUTION}, {period_days + 20} days)",
        )
        backtest_trade_strategies(
            _get_data(period_days + 20, settings),
            ComposeStrategiesListMethod.EXTEND,
            settings,
            strategies_file_name_suffix_old=f"dev_{i}",
            strategies_file_name_suffix_new=f"dev_{i + 1}",
        )

    log.warning(f"Backtesting strategies for {settings.NAME} ({settings.RESOLUTION}, {period_days} days)")
    backtest_trade_strategies(
        _get_data(period_days, settings),
        ComposeStrategiesListMethod.READ,
        settings,
        strategies_file_name_suffix_old=f"dev_{settings.TRADING_STRATEGY_INDICATORS}",
    )


if __name__ == "__main__":
    try:
        generate_strategies(SETTINGS_TRADE_STRATEGIES_GULD, period_days=40)
        generate_strategies(SETTINGS_TRADE_STRATEGIES_OMX, period_days=40)

        for instrument, account_id in [
            ("GULD", SETTINGS_TRADE_STRATEGIES_GULD.ACCOUNT_ID),
            ("OMX", SETTINGS_TRADE_STRATEGIES_OMX.ACCOUNT_ID),
        ]:
            reset_file_handlers(f"deals_{instrument}")
            Transactions(account_id).log_deals(log_header=f"trade_{instrument}")

            portfolio = Portfolio(account_id)
            portfolio.reload_balance()
            log.info(f"Portfolio balance: {portfolio.total_value}")
            log.info("------------")

    except Exception as e:
        telegram = Telegram()
        telegram.messages = ["Error in task_eow.py"]
        telegram.send_message()

        raise e
