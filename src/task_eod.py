import platform
import warnings
from datetime import date, datetime, timedelta

import pandas_market_calendars as mcal
from avanza.constants import Resolution, TimePeriod
from workalendar.europe import Sweden

from apis.avanza.client import get_client
from apis.avanza.operators import Chart
from apis.investing.client.models import Resolution as InvestingResolution
from apis.investing.operators import Ticker as InvestingTicker
from apis.telegram.operators import Telegram
from apis.yahoo.client.models import Interval, Period
from apis.yahoo.operators import Ticker as YahooTicker
from backtest import backtest
from data.settings import SETTINGS
from services.analytics import Analytics, AnalyticsType
from services.storage import Storage
from services.ta.strategies.models import ComposeStrategiesListMethod
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)

set_handlers("eod")
log = get_logger()

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


def get_exchange_working_hours(shift_days: int = 0):
    analytics = Analytics(type=AnalyticsType.EXCHANGE_WORKING_HOURS)
    analytics.read_file()

    calendar = Sweden()
    target_date = calendar.add_working_days(date.today(), shift_days)

    if not analytics.data or [i.open for i in analytics.data if i.open][0].date() != target_date:
        update_exchange_working_hours(shift_days)

    log.info("Get exchange working hours for " + ("today" if shift_days == 0 else str(target_date)))

    exchange_working_hours = {}
    for exchange in analytics.data:
        if not exchange.open or not exchange.close:
            continue

        exchange_working_hours.setdefault(str(exchange.open.time()), []).append(f"open - {exchange.name}")
        exchange_working_hours.setdefault(str(exchange.close.time()), []).append(f"close - {exchange.name}")

    return dict(sorted(exchange_working_hours.items()))


def cache_history(settings):
    log.warning(f"TASK: Cache {settings.NAME} data")

    for resolution_ava, resolution_investing, interval_yahoo in [
        (Resolution.MINUTE, InvestingResolution.ONE_MINUTE, Interval.ONE_MINUTE),
        (Resolution.TWO_MINUTES, None, Interval.TWO_MINUTES),
        (Resolution.FIVE_MINUTES, InvestingResolution.FIVE_MINUTES, Interval.FIVE_MINUTES),
        (Resolution.HOUR, InvestingResolution.SIXTY_MINUTES, Interval.SIXTY_MINUTES),
    ]:
        storage = Storage(settings, resolution=interval_yahoo.value.raw)
        rows_before = storage.read().shape[0]

        data_ava = Chart.get_chart_data(settings, TimePeriod.TODAY, resolution_ava)
        storage.write(data_ava)

        if False and resolution_investing and platform.system() == "Darwin":
            for i in range(5, 60, 5):
                data_investing = InvestingTicker(settings).get_history(
                    resolution=resolution_investing,
                    period_days=i,
                )
                storage.write(data_investing)

        if storage.read().shape[0] == rows_before:
            data_yahoo = YahooTicker(settings).get_history(period=Period.FIVE_DAYS, interval=interval_yahoo)
            storage.write(data_yahoo)

        rows_after = storage.read().shape[0]
        log.info(f"Cached ({interval_yahoo.value.raw}): {rows_before} rows before -> {rows_after} rows after")


def backtest_strategies(settings):
    period_days = 20

    log.warning(f"TASK: Backtest strategies on {settings.NAME} | {settings.RESOLUTION} | {period_days} days")

    data = Storage(settings).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    backtest(
        data,
        [],
        ComposeStrategiesListMethod.READ,
        settings,
        old_strategies_file_name="strategies_dev_7_indicators.json",
        new_strategies_file_name="strategies.json",
        plot=False,
    )


def gather_analytics():
    log.warning("TASK: Gather analytics")

    update_exchange_working_hours(shift_days=1)
    exchange_working_hours = get_exchange_working_hours(shift_days=1)
    if not exchange_working_hours:
        log.info("No upcoming events")
    else:
        for daytime, events in exchange_working_hours.items():
            if any(
                [
                    datetime.strptime(daytime, "%H:%M:%S") <= datetime.strptime("09:00", "%H:%M"),
                    datetime.strptime(daytime, "%H:%M:%S") >= datetime.strptime("23:00", "%H:%M"),
                ],
            ):
                continue

            log.info(f"{daytime}: {', '.join(events)}")


if __name__ == "__main__":
    try:
        for settings in (SETTINGS.OMX, SETTINGS.NASDAQ):
            cache_history(settings)
            backtest_strategies(settings)

        gather_analytics()

    except Exception as e:
        telegram = Telegram()
        telegram.messages = ["Error in task_eod.py"]
        telegram.send_message()

        raise e
