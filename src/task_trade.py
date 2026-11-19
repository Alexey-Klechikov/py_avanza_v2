import warnings

import pandas as pd

from apis.telegram.operators import Telegram
from config import DRY_RUN, SETTINGS
from tasks.trade.main import trade
from utils.logger.operators import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None

set_handlers("trade")
log = get_logger()


if __name__ == "__main__":
    try:
        trade()

    except Exception as error:
        log.exception(str(error))

        if not DRY_RUN:
            telegram = Telegram()
            telegram.messages = [f"Error in task_trade {SETTINGS.NAME}"]
            telegram.send_message()

        raise error
