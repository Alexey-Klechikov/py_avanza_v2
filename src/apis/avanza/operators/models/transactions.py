from dataclasses import dataclass

from apis.avanza.client.models.order.transactions import Transaction


@dataclass
class Deal:
    buy: Transaction | None = None
    sell: Transaction | None = None
