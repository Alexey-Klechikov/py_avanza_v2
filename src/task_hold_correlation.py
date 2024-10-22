import platform
import warnings

import pandas as pd

from apis.telegram.operators import Telegram as TelegramBase
from config import SETTINGS_HOLD_CORRELATION
from hold_correlation import hold
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

set_handlers("hold_correlation")
log = get_logger()


if __name__ == "__main__":
    try:
        dry_run = platform.system() == "Darwin"

        hold(dry_run, SETTINGS_HOLD_CORRELATION)

    except Exception as e:
        log.exception(str(e))

        telegram = TelegramBase()
        telegram.messages = ["Error in task_hold.py"]
        telegram.send_message()

        raise e
