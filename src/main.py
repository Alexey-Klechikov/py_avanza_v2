import warnings

from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)


set_handlers("WIP")
log = get_logger()


# omx_30 = "19002"
def tests_avanza():
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

    # data = Chart.get_chart_data("19002", TimePeriod.ONE_MONTH, Resolution.HOUR)
    # print(data)
    # return data

    ###############
    # from services.avanza.operators.instrument import Instrument
    # from avanza.constants import InstrumentType

    # 1628492 - cert
    # 19002 - index
    # 1734794 - WARRANT
    # stock - 5447

    # print(Instrument.get(instrument_id="1628492", instrument_type=InstrumentType.CERTIFICATE))

    return


def tests_yahoo():
    ############
    # from services.yahoo.client.models import Interval, Period
    # from services.yahoo.operators import Ticker
    # from data.settings import OMX30_YAHOO

    # data = Ticker(OMX30_YAHOO).get_history(period=Period.ONE_YEAR, interval=Interval.SIXTY_MINUTES)
    # print(data)
    # return data

    return


def tests_storage(data_ava, data_yahoo):
    ############
    # from services.storage import Storage

    # from data.settings import OMX30_YAHOO

    # from services.yahoo.client.models import Interval, Period

    # data = Storage(OMX30_YAHOO, period="1y", interval="60m", cache="reuse")

    # Storage(OMX30_YAHOO, resolution="60m").write(data_yahoo)
    # Storage(OMX30_YAHOO, resolution="60m").append(data_ava)

    # print(Storage(OMX30_YAHOO, resolution="60m").read())

    return


if __name__ == "__main__":
    data_ava = tests_avanza()
    data_yahoo = tests_yahoo()
    tests_storage(data_ava, data_yahoo)
