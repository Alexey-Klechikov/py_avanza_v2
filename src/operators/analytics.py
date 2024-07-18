from datetime import date

from workalendar.europe import Sweden

from apis.avanza.client import get_client
from services.analytics import Analytics
from utils.logger import get_logger

log = get_logger()


def update_stock_events():
    log.info("Update stock events")

    analytics = Analytics()
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
    analytics = Analytics()
    analytics.read_file()

    calendar = Sweden()
    target_date = calendar.add_working_days(date.today(), shift_days)

    log.info("Get events for " + ("today" if shift_days == 0 else str(target_date)))
    stock_events = []
    for stock in analytics.data:
        for event in stock.company_events:
            if event.date == target_date:
                stock_events.append(f"{stock.name}: {event.type}")

        for event in stock.dividends:
            if event.ex_date == target_date:
                stock_events.append(f"{stock.name}: Dividend. Amount: {event.amount} {event.currency_code}")

    return stock_events
