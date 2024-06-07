from src.utils.logger import get_logger, set_handlers

set_handlers("WIP")
log = get_logger("main")

# omx_30 = "19002"

###############
# from src.operators.avanza_bank import Watchlists
# wl = Watchlists(get_client())
# wl.update_watchlists()
# wl.get_watchlists()

###############
# from src.operators.avanza_bank import Balance
# bl = Balance(get_client())
# bl.get_balance()
# print(bl.total_value)
# print(bl.buying_power)


###############
# from src.clients.avanza_bank import get_client
# from src.operators.avanza_bank import Orders
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
# print(ord.active_order)
# ord.edit_active(new_price=31)
# print(ord.active_order)
