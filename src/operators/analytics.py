from datetime import date

import pandas_market_calendars as mcal
from workalendar.europe import Sweden

from apis.avanza.client import get_client
from services.analytics import Analytics, AnalyticsType
from utils.logger import get_logger

log = get_logger()


def update_stock_events():
    log.info("Update stock events")

    analytics = Analytics(type=AnalyticsType.STOCK_EVENTS)
    analytics.read_file()

    for stock in analytics.data:
        log.debug(f"Stock: {stock.name}")

        instrument = get_client().get_instrument_stock(stock.order_book_id)
        if not instrument:
            continue

        stock.company_events = instrument.company_events.events
        stock.dividends = instrument.dividends.events

    analytics.write_file()


def get_stock_events(shift_days: int = 0):
    analytics = Analytics(type=AnalyticsType.STOCK_EVENTS)
    analytics.read_file()

    calendar = Sweden()
    target_date = calendar.add_working_days(date.today(), shift_days)

    log.info("Get events for " + ("today" if shift_days == 0 else str(target_date)))

    stock_events_by_date = {}
    for stock in analytics.data:
        for event in stock.company_events:
            stock_events_by_date.setdefault(event.date, []).append(f"{stock.name}: {event.type}")

        for event in stock.dividends:
            stock_events_by_date.setdefault(event.ex_date, []).append(
                f"{stock.name}: Dividend. Amount: {event.amount} {event.currency_code}",
            )

    return stock_events_by_date.get(target_date, [])


def update_exchange_working_hours(shift_days: int = 0):
    analytics = Analytics(type=AnalyticsType.EXCHANGE_WORKING_HOURS)
    analytics.read_file()

    calendar = Sweden()
    target_date = calendar.add_working_days(date.today(), shift_days)

    log.info("Update exchange working hours for " + ("today" if shift_days == 0 else str(target_date)))

    for exchange in analytics.data:
        log.debug(f"Exchange: {exchange.name}")

        exchange_calendar = mcal.get_calendar(exchange.code)

        schedule = exchange_calendar.schedule(
            start_date=target_date,
            end_date=target_date,
            tz="Europe/Stockholm",
        )

        if schedule.empty:
            exchange.open = None
            exchange.close = None
            continue

        exchange.open = schedule.iloc[0].market_open
        exchange.close = schedule.iloc[0].market_close

    analytics.write_file()
