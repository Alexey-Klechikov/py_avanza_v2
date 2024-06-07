from utils.logger import get_logger, set_handlers

set_handlers("WIP")
log = get_logger("main")

# omx_30 = "19002"

##############
# from avanza_bank.client import get_client
# from avanza_bank.operators import Watchlists
# wl = Watchlists(get_client())
# wl.update_watchlists()
# wl.refresh_watchlists()

# print(wl.valid_instruments)
# print(wl.preferred_instrument)


###############
# from avanza_bank.client import get_client
# from avanza_bank.operators import Portfolio
# bl = Portfolio(get_client())
# bl.refresh_balance()
# bl.refresh_positions()

# print(bl.total_value)
# print(bl.buying_power)
# print(bl.positions)


###############
# from avanza_bank.client import get_client
# from avanza_bank.operators import Orders
# from avanza.constants import OrderType

# account_id = "5554179"
# order_book_id = "1478248"
# order_type = OrderType.BUY
# price = 30
# volume = 1

# ord = Orders(get_client())
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
# from avanza_bank.client import get_client
# from avanza_bank.operators import Chart

# ch = Chart(get_client())
# print(ch.get_chart_data("19002", TimePeriod.TODAY, Resolution.MINUTE))
