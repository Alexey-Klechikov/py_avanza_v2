import warnings

from apis.avanza.operators.portfolio import Portfolio
from apis.telegram.operators import Telegram
from config import SETTINGS
from services.storage.operators import Storage
from services.storage.windows import CalibrationWindows
from services.ta.strategies.models.strategy import ComposeStrategiesListMethod
from tasks.backtest.runner import backtest_trade_strategies
from utils.constants import TODAY_MIDNIGHT
from utils.logger.operators import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.simplefilter(action="ignore", category=UserWarning)

set_handlers("end_of_week")
log = get_logger()


def generate_strategies() -> bool:
    """Train on TRAIN_DAYS that end HOLDOUT_DAYS ago, then final-test on the unseen last HOLDOUT_DAYS."""
    windows = CalibrationWindows.ending(TODAY_MIDNIGHT)
    cached_bars = Storage().read()
    training_bars = windows.training.slice(cached_bars)
    holdout_bars = windows.holdout.slice(cached_bars)
    log.info(f"Training on {windows.training}, final test on {windows.holdout}")

    log.warning(
        f"Long-test strategies for {SETTINGS.NAME} ({SETTINGS.RESOLUTION}, {SETTINGS.STRATEGY.TRAIN_DAYS} days)",
    )
    backtest_trade_strategies(
        training_bars.copy(),
        ComposeStrategiesListMethod.GENERATE,
        strategies_file_name_suffix_new=f"dev_{SETTINGS.STRATEGY.INDICATORS_START}",
    )

    for indicators_count in range(SETTINGS.STRATEGY.INDICATORS_START, SETTINGS.STRATEGY.INDICATORS):
        log.warning(
            f"Long-test strategies ({indicators_count} -> {indicators_count + 1}) for {SETTINGS.NAME} "
            f"({SETTINGS.RESOLUTION}, {SETTINGS.STRATEGY.TRAIN_DAYS} days)",
        )
        backtest_trade_strategies(
            training_bars.copy(),
            ComposeStrategiesListMethod.EXTEND,
            strategies_file_name_suffix_old=f"dev_{indicators_count}",
            strategies_file_name_suffix_new=f"dev_{indicators_count + 1}",
        )

    log.warning(
        f"Final-test strategies for {SETTINGS.NAME} ({SETTINGS.RESOLUTION}, {SETTINGS.STRATEGY.HOLDOUT_DAYS} days)",
    )
    final_strategies = backtest_trade_strategies(
        holdout_bars,
        ComposeStrategiesListMethod.READ,
        strategies_file_name_suffix_old=f"dev_{SETTINGS.STRATEGY.INDICATORS}",
    )
    return bool(final_strategies)


if __name__ == "__main__":
    try:
        if not generate_strategies():
            telegram = Telegram()
            telegram.messages = ["task_eow.py: no strategy clears STRATEGY.MIN_EDGE in the final test; trading paused"]
            telegram.send_message()

        portfolio = Portfolio()
        portfolio.reload_balance()
        log.info(f"Portfolio balance: {portfolio.total_value}")
        log.info("------------")

    except Exception as e:
        telegram = Telegram()
        telegram.messages = ["Error in task_eow.py"]
        telegram.send_message()

        raise e
