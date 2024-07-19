from datetime import date

import pandas_market_calendars as mcal
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

    stock_events_by_date = {}
    for stock in analytics.data:
        for event in stock.company_events:
            stock_events_by_date.setdefault(event.date, []).append(f"{stock.name}: {event.type}")

        for event in stock.dividends:
            stock_events_by_date.setdefault(event.ex_date, []).append(
                f"{stock.name}: Dividend. Amount: {event.amount} {event.currency_code}",
            )

    return stock_events_by_date.get(target_date, [])


def get_stock_exchange_working_hours(shift_days: int = 0):  # WIP
    exchanges = {
        "TASE": "Tel-Aviv",
        "NYSE": "New York",
        "TSX": "Toronto",
        "SSE": "Shanghai",
        "SIX": "Zurich",
        "OSE": "Oslo",
        "LSE": "London",
        "JPX": "Tokyo",
        "HKEX": "Hong Kong",
        "BSE": "Mumbai",
        "BMF": "Sao Paulo",
        "ASX": "Sydney",
        # Futures Exchange
        "CME_Equity": "CME US",
        "CFE": "CBOE US",
        # Intercontinental Exchange
        "ICE": "ICE US",
        # Investors Exchange
        "IEX": "IEX US",
        # Securities Industry and Financial Markets Association
        "SIFMA_US": "SIFMA US",
        "SIFMA_UK": "SIFMA UK",
        "SIFMA_JP": "SIFMA Japan",
    }

    for excange_code, excange_name in exchanges.items():
        log.info(f"Exchange: {excange_name}")

        exchange = mcal.get_calendar(excange_code)

        schedule = exchange.schedule(start_date=date.today(), end_date=date.today(), tz="Europe/Stockholm")

        for _, row in schedule.iterrows():
            log.info(f"Open: {row['market_open']} - {row['market_close']}")
