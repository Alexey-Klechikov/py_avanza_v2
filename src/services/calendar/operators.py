from datetime import datetime, time, timedelta

import pandas_market_calendars as mcal
import pytz


def market_is_close() -> bool:
    now = datetime.now(tz=pytz.timezone("Europe/Berlin"))
    today = datetime.today().strftime("%Y-%m-%d")

    sto = mcal.get_calendar("XSTO")
    schedule = sto.schedule(start_date=today, end_date=today, tz="Europe/Berlin").iloc[0]

    return not (schedule.market_open <= now <= schedule.market_close)


def get_market_close_time() -> time:
    today = datetime.today().strftime("%Y-%m-%d")

    sto = mcal.get_calendar("XSTO")
    try:
        market_close_time = sto.schedule(start_date=today, end_date=today, tz="Europe/Berlin").iloc[
            0
        ].market_close - timedelta(minutes=11)

        return market_close_time.replace(tzinfo=None).time()

    except IndexError:
        return datetime.now().time()
