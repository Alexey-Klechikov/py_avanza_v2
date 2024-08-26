from datetime import date, timedelta
from time import sleep
from typing import List, Optional

from avanza.constants import OrderType

from apis.avanza.client import get_client
from apis.avanza.client.models import Deal, Order, OrderException
from data.settings import AVANZA_ACCOUNT
from utils.logger import get_logger

log = get_logger()


class Orders:
    def __init__(self):
        self.active_order: Optional[Order] = None

    def reload_active(self):
        self.active_order = None

        orders = get_client().list_orders().orders
        orders = [i for i in orders if i.account.account_id == AVANZA_ACCOUNT.ACCOUNT_ID]

        active_orders = [i for i in orders if i.state in ("ACTIVE", "ACTIVE_PENDING")]
        if not active_orders:
            return

        self.active_order = max(active_orders, key=lambda x: x.created)
        log.debug(f"Active orders found [{len(active_orders)} st.]")

        for order in active_orders:
            if order.order_id == self.active_order.order_id:
                continue
            self._delete(order.order_id)

        inactive_orders = [i for i in orders if i.state == "FAILED"]
        if len(inactive_orders) > 0:
            log.warning(f"Inactive order(s) found ({len(inactive_orders)} st)")
            for order in inactive_orders:
                self._delete(order.order_id)

    def get_past(self) -> List[Deal]:
        return sorted(
            [i for i in get_client().get_past_orders().deals if i.account.account_id == AVANZA_ACCOUNT.ACCOUNT_ID],
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
        if not price:
            log.warning("No price set for order: %s %s", order_book_id, order_type.value)
            return

        try:
            _ = get_client().place_order(
                account_id=AVANZA_ACCOUNT.ACCOUNT_ID,
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

    def _delete(self, order_id: str) -> Optional[str]:
        try:
            _ = get_client().delete_order(account_id=AVANZA_ACCOUNT.ACCOUNT_ID, order_id=order_id)

            log.info("Order deleted")

        except OrderException as exc:
            log.error(f"Exception: {exc}")

    def delete_all(self):
        orders = get_client().list_orders().orders
        orders = [i for i in orders if i.account.account_id == AVANZA_ACCOUNT.ACCOUNT_ID]

        for order in orders:
            self._delete(order.order_id)
