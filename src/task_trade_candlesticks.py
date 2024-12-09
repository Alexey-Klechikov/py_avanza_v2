import platform
import warnings

import pandas as pd

from apis.telegram.operators import Telegram as TelegramBase
from config import SETTINGS_TRADE_CANDLESTICKS
from tasks.trade_candlesticks.main import trade
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

set_handlers("trade_candlesticks")
log = get_logger()


if __name__ == "__main__":
    dry_run = platform.system() == "Darwin"
    try:
        trade(dry_run, SETTINGS_TRADE_CANDLESTICKS)

    except Exception as e:
        log.exception(str(e))

        if not dry_run:
            telegram = TelegramBase()
            telegram.messages = ["Error in task_trade_candlesticks"]
            telegram.send_message()

        raise e
