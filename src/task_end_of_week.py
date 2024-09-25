import warnings
from datetime import datetime, timedelta

from apis.telegram.operators import Telegram
from backtest import backtest
from config import SETTINGS_TRADE_NASDAQ, SETTINGS_TRADE_OMX
from services.storage import Storage
from services.ta.strategies.models import ComposeStrategiesListMethod
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.simplefilter(action="ignore", category=UserWarning)

set_handlers("end_of_week")
log = get_logger()


def generate_strategies(settings) -> None:
    period_days = 60

    data = Storage(settings).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    log.warning(f"Generating strategies for {settings.NAME} ({settings.RESOLUTION}, {period_days} days)")
    backtest(
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
        backtest(
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
    backtest(
        data,
        ComposeStrategiesListMethod.READ,
        settings,
        old_strategies_file_name=f"strategies_dev_{settings.TRADING_STRATEGY_INDICATORS}.json",
        new_strategies_file_name="strategies.json",
        plot=False,
    )


if __name__ == "__main__":
    try:
        for settings in (SETTINGS_TRADE_OMX, SETTINGS_TRADE_NASDAQ):
            generate_strategies(settings)

    except Exception as e:
        telegram = Telegram()
        telegram.messages = ["Error in task_eow.py"]
        telegram.send_message()

        raise e
