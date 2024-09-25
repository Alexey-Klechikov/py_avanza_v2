from datetime import date, timedelta
from time import sleep
from typing import List, Optional

from avanza.constants import OrderType

from apis.avanza.client import get_client
from apis.avanza.client.models import Deal, Order, OrderException
from utils.logger import get_logger

log = get_logger()


class Orders:
    def __init__(
        self,
        account_id: str,
        filter_side: Optional[str] = None,
        filter_orderbook_direction: Optional[str] = None,
        filter_orderbook_name: Optional[str] = None,
        dry_run: bool = False,
    ):
        self.active_order: Optional[Order] = None

        self.account_id = account_id
        self.filter_side = filter_side
        self.filter_orderbook_direction = filter_orderbook_direction
        self.filter_orderbook_name = filter_orderbook_name

        self.dry_run = dry_run

    def reload_active(self):
        self.active_order = None

        orders = get_client().list_orders().orders
        orders = [i for i in orders if i.account.account_id == self.account_id]

        active_orders = [i for i in orders if i.state in ("ACTIVE", "ACTIVE_PENDING")]
        if self.filter_side:
            active_orders = [i for i in active_orders if i.side == self.filter_side]
        if self.filter_orderbook_direction:
            active_orders = [i for i in active_orders if self.filter_orderbook_direction in i.orderbook.name]
        if self.filter_orderbook_name:
            active_orders = [i for i in active_orders if self.filter_orderbook_name in i.orderbook.name]
        if not active_orders:
            return

        self.active_order = max(active_orders, key=lambda x: x.created)
        log.debug(f"Active orders found [{len(active_orders)} st.]")

        for order in active_orders:
            if order.order_id == self.active_order.order_id:
                continue
            self.delete(order.order_id)

        inactive_orders = [i for i in orders if i.state == "FAILED"]
        if len(inactive_orders) > 0:
            log.warning(f"Inactive order(s) found ({len(inactive_orders)} st)")
            for order in inactive_orders:
                self.delete(order.order_id)

    def get_past(self) -> List[Deal]:
        return sorted(
            [i for i in get_client().get_past_orders().deals if i.account.account_id == self.account_id],
            key=lambda x: x.time,
        )

    def edit_active(self, new_price: float):
        try:
            if not self.active_order:
                log.warning("No active order found")
                return

            _ = get_client().edit_order(
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

    def place(
        self,
        order_book_id: str,
        instrument_name: str,
        order_type: OrderType,
        price: Optional[float],
        volume: int,
        valid_until: date = date.today() + timedelta(days=7),
    ) -> Optional[str]:
        if self.dry_run:
            log.warning(f"Dry run: {order_type.value} order not placed")

        if not price:
            log.warning("No price set for order: %s %s", order_book_id, order_type.value)
            return

        try:
            _ = get_client().place_order(
                account_id=self.account_id,
                order_book_id=order_book_id,
                order_type=order_type,
                price=price,
                volume=volume,
                valid_until=valid_until,
            )

            log.info("Order placed: %s %s %s", instrument_name, order_type.value, price)

            sleep(3)

            self.reload_active()

        except OrderException as exc:
            log.error(f"Exception: {exc}")

    def delete(self, order_id: str) -> Optional[str]:
        if self.dry_run:
            log.warning("Dry run: DELETE order not placed")

        try:
            _ = get_client().delete_order(account_id=self.account_id, order_id=order_id)

            log.info("Order deleted")

        except OrderException as exc:
            log.error(f"Exception: {exc}")

    def delete_all(self):
        orders = get_client().list_orders().orders
        orders = [i for i in orders if i.account.account_id == self.account_id]

        for order in orders:
            self.delete(order.order_id)
