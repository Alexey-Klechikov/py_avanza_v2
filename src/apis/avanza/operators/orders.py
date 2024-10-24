from datetime import date, timedelta
from time import sleep

from avanza.constants import OrderType

from apis.avanza.client import get_client
from apis.avanza.client.models import Deal, Order, OrderException
from utils.logger import get_logger

log = get_logger()


class Orders:
    def __init__(
        self,
        account_id: str,
        filter_orderbook_direction: str | None = None,
        filter_orderbook_name: str | None = None,
        dry_run: bool = False,
    ):
        self.active_order: Order | None = None

        self.account_id = account_id
        self.filter_orderbook_direction = filter_orderbook_direction
        self.filter_orderbook_name = filter_orderbook_name

        self.dry_run = dry_run

    def _list(self) -> list[Order]:
        orders = get_client().list_orders().orders

        if self.account_id:
            orders = [i for i in orders if i.account.account_id == self.account_id]
        if self.filter_orderbook_direction:
            orders = [i for i in orders if self.filter_orderbook_direction in i.orderbook.name]
        if self.filter_orderbook_name:
            orders = [i for i in orders if self.filter_orderbook_name in i.orderbook.name]

        return orders

    def place(
        self,
        order_book_id: str,
        instrument_name: str,
        order_type: OrderType,
        price: float | None,
        volume: int,
        valid_until: date = date.today() + timedelta(days=7),
    ) -> str | None:
        if self.dry_run:
            log.warning(f"Dry run: {order_type.value} order not placed")

        if not price:
            log.warning("No price set for order: %s %s", order_book_id, order_type.value)
            return

        try:
            get_client().place_order(
                account_id=self.account_id,
                order_book_id=order_book_id,
                order_type=order_type,
                price=price,
                volume=volume,
                valid_until=valid_until,
            )
            log.info(f"Order placed: {order_type.value} {instrument_name} {price}")

            sleep(3)

        except OrderException as exc:
            log.error(f"Exception: {exc}")

    def delete(self, order: Order) -> str | None:
        if self.dry_run:
            log.warning("Dry run: DELETE order not placed")
            return

        try:
            get_client().delete_order(account_id=self.account_id, order_id=order.order_id)
            log.info(f"Order deleted: {order.side} {order.orderbook.name} {order.price} [{order.state}]")

        except OrderException as exc:
            log.error(f"Exception: {exc}")

    def get_past(self) -> list[Deal]:
        past_orders = get_client().get_past_orders().deals
        past_orders = [i for i in past_orders if i.account.account_id == self.account_id]

        return sorted(past_orders, key=lambda x: x.time)

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

    def delete_all(self):
        for order in self._list():
            self.delete(order)
