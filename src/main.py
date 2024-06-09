import warnings

from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)


set_handlers("WIP")
log = get_logger()


# omx_30 = "19002"
def tests_avanza():
    pass
    ##############
    # from services.avanza.operators import Watchlists
    # wl = Watchlists()
    # wl.update_watchlists()
    # wl.refresh_watchlists()

    # print(wl.valid_instruments)
    # print(wl.preferred_instrument)

    ###############
    # from services.avanza.operators import Portfolio
    # bl = Portfolio()
    # bl.refresh_balance()
    # bl.refresh_positions()

    # print(bl.total_value)
    # print(bl.buying_power)
    # print(bl.positions)

    ###############
    # from services.avanza.operators import Orders
    # from avanza.constants import OrderType

    # account_id = "5554179"
    # order_book_id = "1478248"
    # order_type = OrderType.BUY
    # price = 30
    # volume = 1

    # ord = Orders()
    # ord.delete_all()
    # ord.reload_active()
    # ord.place(order_book_id, order_type, price, volume)
    # print(ord.active_order, "\n")

    # ord.edit_active(new_price=31)
    # print(ord.active_order, "\n")

    # ord.delete_all()
    # ord.reload_active()
    # print(ord.active_order)

    ###############
    # from avanza.constants import Resolution, TimePeriod
    # from services.avanza.operators import Chart

    # ch = Chart()
    # print(ch.get_chart_data("19002", TimePeriod.TODAY, Resolution.MINUTE))


def tests_yahoo():
    pass
    ###############
    # from services.yahoo.client.models import Interval, Period
    # from services.yahoo.operators import Ticker

    # data = Ticker.get_history(ticker_yahoo="OMX", period=Period.ONE_YEAR, interval=Interval.ONE_MINUTE)
    # print(data)
