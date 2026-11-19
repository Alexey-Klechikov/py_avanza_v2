from datetime import datetime, time, timedelta

import pandas as pd
import pandas_market_calendars as mcal
import pytz

TIMEZONE = "Europe/Stockholm"
STOP_BEFORE_CLOSE = timedelta(minutes=11)


def _today_nyse_schedule() -> pd.DataFrame:
    """Today's NYSE session in Stockholm time: one row, or none on a day without a session."""
    today = datetime.today().strftime("%Y-%m-%d")

    return mcal.get_calendar("XNYS").schedule(start_date=today, end_date=today, tz=TIMEZONE)


def is_market_closed() -> bool:
    schedule = _today_nyse_schedule()
    if schedule.empty:
        return True

    session = schedule.iloc[0]
    now = datetime.now(tz=pytz.timezone(TIMEZONE))

    return not (session.market_open <= now <= session.market_close)


def get_trading_end_time() -> time:
    """STOP_BEFORE_CLOSE before today's NYSE close, as Stockholm wall-clock time. On a day without a session (a US
    holiday on a cron weekday) it is midnight, so the live loop's first end-of-day check stops trading at once."""
    schedule = _today_nyse_schedule()
    if schedule.empty:
        return time.min

    return (schedule.iloc[0].market_close - STOP_BEFORE_CLOSE).replace(tzinfo=None).time()
