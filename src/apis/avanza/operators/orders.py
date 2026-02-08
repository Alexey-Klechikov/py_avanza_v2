from datetime import date, timedelta
from time import sleep

from avanza.constants import OrderType

from apis.avanza.client.client import get_client
from apis.avanza.client.models.order.exceptions import OrderException
from apis.avanza.client.models.order.list import Order
from config import SETTINGS
from utils.logger.operators import get_logger

log = get_logger()


class Orders:
    def __init__(self, filter_orderbook_direction: str | None = None):
        self.active_order: Order | None = None

        self.filter_orderbook_direction = filter_orderbook_direction

    def _list(self) -> list[Order]:
        orders = get_client().list_orders().orders

        if SETTINGS.ACCOUNT_ID:
            orders = [i for i in orders if i.account.account_id == SETTINGS.ACCOUNT_ID]
        if self.filter_orderbook_direction:
            orders = [i for i in orders if self.filter_orderbook_direction in i.orderbook.name]
        if SETTINGS.NAME:
            orders = [i for i in orders if SETTINGS.NAME in i.orderbook.name]

        return orders

    def place(
        self,
        order_book_id: str,
        instrument_name: str,
        order_type: OrderType,
        price: float | None,
        volume: int,
        valid_until: date = date.today() + timedelta(days=7),
        caller: str = "",
    ) -> str | None:
        if SETTINGS.DRY_RUN:
            log.warning(f"Dry run: {order_type.value} order not placed")

        if not price:
            log.warning("No price set for order: %s %s", order_book_id, order_type.value)
            return

        try:
            get_client().place_order(
                account_id=SETTINGS.ACCOUNT_ID,
                order_book_id=order_book_id,
                order_type=order_type,
                price=price,
                volume=volume,
                valid_until=valid_until,
            )
            log.info(
                (f"[{caller}] " if caller else "") + f"Order placed: {order_type.value} {instrument_name} {price}",
            )

            sleep(3)

        except OrderException as exc:
            log.error(f"Exception: {exc}")

    def delete(self, order: Order, caller: str = "") -> str | None:
        if SETTINGS.DRY_RUN:
            log.warning("Dry run: DELETE order not placed")
            return

        try:
            get_client().delete_order(account_id=SETTINGS.ACCOUNT_ID, order_id=order.order_id)
            log.info(
                (f"[{caller}] " if caller else "")
                + f"Order deleted: {order.side} {order.orderbook.name} {order.price} [{order.state}]",
            )

        except OrderException as exc:
            log.error(f"Exception: {exc}")

    def reload_active(self):
        self.active_order = None

        orders = self._list()
        if not orders:
            log.debug("No orders found")
            return

        active_orders = [i for i in orders if i.state in ("ACTIVE", "ACTIVE_PENDING")]
        if active_orders:
            self.active_order = max(active_orders, key=lambda x: x.created)
            log.debug(f"Active orders found [{len(active_orders)} st.]")

        for order in orders:
            if self.active_order and self.active_order.order_id == order.order_id:
                continue

            self.delete(order)

    def edit_active(self, new_price: float):
        if not self.active_order:
            log.warning("No active order found")
            return

        try:
            get_client().edit_order(
                self.active_order.order_id,
                self.active_order.account.account_id,
                new_price,
                self.active_order.valid_until.date(),
                self.active_order.volume,
            )

            self.active_order.price = new_price
            self.active_order.amount = new_price * self.active_order.volume

            log.info("Order edited")

        except OrderException as exc:
            log.error(f"Exception: {exc}")

    def delete_all(self, caller: str = ""):
        for order in self._list():
            self.delete(order, caller)
