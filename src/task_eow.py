import warnings
from datetime import datetime, timedelta
from typing import List, Tuple

from apis.telegram.operators import Telegram
from backtest import backtest
from data.settings import OMX30_YAHOO
from services.storage import Storage
from services.ta.strategies.models import ComposeStrategiesListMethod
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.simplefilter(action="ignore", category=UserWarning)

set_handlers("eow")
log = get_logger()


def generate_strategies(indicators_selector: List[Tuple[str, str]]):
    resolution = "2m"
    period_days = 60

    data = Storage(OMX30_YAHOO, resolution=resolution).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    log.warning("Generating strategies")
    backtest(
        data,
        indicators_selector,
        ComposeStrategiesListMethod.GENERATE,
        old_strategies_file_name=None,
        new_strategies_file_name="strategies_dev_3_indicators.json",
        indicators_filter=[],
        plot=False,
    )

    for i in range(3, 7):
        log.warning(f"Extending strategies ({i} -> {i + 1})")
        backtest(
            data,
            indicators_selector,
            ComposeStrategiesListMethod.EXTEND,
            old_strategies_file_name=f"strategies_dev_{i}_indicators.json",
            new_strategies_file_name=f"strategies_dev_{i + 1}_indicators.json",
            indicators_filter=[],
            plot=False,
        )

    resolution = "2m"
    period_days = 20

    data = Storage(OMX30_YAHOO, resolution=resolution).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    log.warning("Backtesting strategies")
    backtest(
        data,
        indicators_selector,
        ComposeStrategiesListMethod.READ,
        old_strategies_file_name="strategies_dev_7_indicators.json",
        new_strategies_file_name="strategies.json",
        indicators_filter=[],
        plot=False,
    )


if __name__ == "__main__":
    indicators_selector = [
        ("Trend", "ADX"),  # buy / sell
        ("Trend", "TII"),  # buy / sell
        ("Trend", "PSAR"),  # buy / sell
        ("Trend", "CHOP"),  # exit
        ("Overlap", "LINREG"),  # buy / sell
        ("Overlap", "SUPERTREND"),  # buy / sell
        ("Momentum", "MACD_DEMA"),  # buy / sell
        ("Momentum", "STC"),  # buy / sell
        ("Momentum", "CCI"),  # buy / sell
        ("Momentum", "RVGI"),  # buy / sell
        ("Momentum", "STOCH"),  # buy / sell
        ("Cycles", "EBSW"),  # buy / sell
        ("Volatility", "STARC"),  # buy / sell
        ("Volatility", "MASSI"),  # buy / sell
        ("Volatility", "BBANDS"),  # buy / sell
        ("Volatility", "ACCBANDS"),  # buy / sell
        ("Volume", "PVT"),  # buy / sell
        ("Volume", "ADOSC"),  # buy / sell
        ("Volume", "CMF"),  # buy / sell
        ("Volume", "KVO"),  # buy / sell
    ]

    try:
        generate_strategies(indicators_selector)

    except Exception as e:
        telegram = Telegram()
        telegram.messages = ["Error in task_eow.py"]
        telegram.send_message()

        raise e
