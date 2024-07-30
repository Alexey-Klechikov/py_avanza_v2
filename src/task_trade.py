import platform
import warnings

import pandas as pd

from apis.telegram.operators import Telegram
from operators import trade
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'


set_handlers("trade")
log = get_logger()


if __name__ == "__main__":
    try:
        trade(dry_run=(True if platform.system() == "Darwin" else False))

    except Exception as e:
        telegram = Telegram()
        telegram.messages = ["Error in task_trade.py"]
        telegram.send_message()

        raise e
