import warnings

from apis.avanza.operators.portfolio import Portfolio
from apis.telegram.operators import Telegram
from services.storage.operators import Storage
from tasks.backtest.model import train_weighted_model
from tasks.backtest.paper_trade import PaperTrack, forward_summary
from utils.logger.operators import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.simplefilter(action="ignore", category=UserWarning)

set_handlers("end_of_week")
log = get_logger()


if __name__ == "__main__":
    try:
        weighted_model = train_weighted_model(Storage().read(), Storage(resolution="1d").read())

        telegram = Telegram()
        telegram.messages = [forward_summary(track) for track in PaperTrack]
        telegram.messages.append(f"Weighted score refitted: {len(weighted_model.weights)} votes kept")
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
