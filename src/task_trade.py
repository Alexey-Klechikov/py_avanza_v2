import warnings

import pandas as pd

from operators import trade
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'


set_handlers("trade")
log = get_logger()


if __name__ == "__main__":
    trade()
