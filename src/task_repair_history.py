"""One-off: replace cached 2-minute candles of the last ~42 days with complete candles from Yahoo.

Until the cache merge kept the newest fetch, candles the live loop stored while still in progress were never
replaced by their completed version. Avanza serves 2-minute candles only for today. Yahoo serves complete ones,
identical to Avanza's where both are complete, for roughly the last 42 days (the Ticker client's cap for 2-minute
history). Older partial-candle days cannot be repaired; the backtest drops them (services/storage/candle_quality.py).
"""

from apis.yahoo.client.models.history_request import Interval, Period
from apis.yahoo.operators.ticker import Ticker
from services.storage.candle_quality import CandleQuality
from services.storage.operators import Storage
from utils.logger.operators import get_logger, set_handlers

set_handlers("repair_history")
log = get_logger()


def _log_quality(label: str, storage: Storage) -> None:
    quality = CandleQuality.of(storage.read())
    log.warning(
        f"{label}: {len(quality.clean_days)} clean days, {len(quality.partial_days)} partial-candle days"
        + (f" (latest partial {quality.partial_days[-1]})" if quality.partial_days else ""),
    )


if __name__ == "__main__":
    storage = Storage()
    _log_quality("Before repair", storage)

    complete_candles = Ticker().get_history(period=Period.THREE_MONTHS, interval=Interval.TWO_MINUTES)
    log.warning(
        f"Fetched {len(complete_candles)} candles: {complete_candles.index.min()} - {complete_candles.index.max()}"
    )
    storage.write(complete_candles)

    _log_quality("After repair", storage)
