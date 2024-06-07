from datetime import date, timedelta
from typing import Optional

from avanza.constants import OrderType

from src.clients.avanza_bank import Avanza
from src.clients.avanza_bank.models import Order, OrderException
from src.data.settings import ACCOUNT_ID
from src.utils.logger import get_logger

log = get_logger("operators.avanza_bank.orders")


class Orders:
    def __init__(self, client: Avanza):
        self.client = client

        self.active_order: Optional[Order] = None

    def reload_active(self):
        self.active_order = None

        orders = self.client.list_orders()

        active_orders = [i for i in orders.orders if i.state == "ACTIVE"]
        if active_orders:
            self.active_order = max(active_orders, key=lambda x: x.created)
            log.info("Active order set")

            if len(active_orders) > 1:
                log.warning(f"More than one active order found ({len(active_orders)})")
                for order in active_orders:
                    if order.order_id != self.active_order.order_id:
                        self._delete(order.order_id)

        inactive_orders = [i for i in orders.orders if i.state == "FAILED"]
        if len(inactive_orders) > 0:
            log.warning(f"Inactive order(s) found ({len(inactive_orders)} st)")
            for order in inactive_orders:
                self._delete(order.order_id)

    def edit_active(self, new_price: float):
        try:
            if not self.active_order:
                log.warning("No active order found")
                return

            _ = self.client.edit_order(
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
        order_type: OrderType,
        price: float,
        volume: int,
        valid_until: date = date.today() + timedelta(days=7),
    ) -> Optional[str]:
        try:
            _ = self.client.place_order(
                account_id=ACCOUNT_ID,
                order_book_id=order_book_id,
                order_type=order_type,
                price=price,
                volume=volume,
                valid_until=valid_until,
            )

            log.info("Order placed")

            self.reload_active()

        except OrderException as exc:
            log.error(f"Exception: {exc}")

    def _delete(self, order_id: str) -> Optional[str]:
        try:
            _ = self.client.delete_order(account_id=ACCOUNT_ID, order_id=order_id)

            log.info("Order deleted")

        except OrderException as exc:
            log.error(f"Exception: {exc}")

    def delete_all(self):
        orders = self.client.list_orders()

        for order in orders.orders:
            self._delete(order.order_id)
