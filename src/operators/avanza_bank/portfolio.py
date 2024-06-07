from typing import List

from avanza.constants import InstrumentType

from src.clients.avanza_bank import Avanza
from src.data.settings import ACCOUNT_ID
from src.operators.avanza_bank.models import Position
from src.utils.logger import get_logger

log = get_logger("operators.avanza_bank.portfolio")


class Portfolio:
    def __init__(self, client: Avanza):
        self.client = client
        self.account_id = ACCOUNT_ID

        self.total_value = 0
        self.buying_power = 0
        self.positions: List[Position] = []

    def refresh_balance(self) -> None:
        log.debug("Refresh account balance")

        accounts_overview = self.client.get_accounts_overview()

        account_overview = [i for i in accounts_overview.accounts if i.info.id == self.account_id][0]

        self.total_value = account_overview.total_value.total_value.value
        self.buying_power = account_overview.buying_power.total.value

    def refresh_positions(self) -> None:
        log.debug("Refresh account positions")

        positions = self.client.get_accounts_positions().with_orderbook
        positions = [i for i in positions if i.account.id == self.account_id]

        self.positions = [
            Position(
                **{
                    "instrument": {
                        "id": i.instrument.id,
                        "type": InstrumentType[i.instrument.type],
                        "name": i.instrument.name,
                    },
                    "quote": {
                        "buy": (
                            None if not i.instrument.orderbook.quote.buy else i.instrument.orderbook.quote.buy.value
                        ),
                        "sell": (
                            None if not i.instrument.orderbook.quote.sell else i.instrument.orderbook.quote.sell.value
                        ),
                    },
                    "volume": i.volume.value,
                    "value": i.value.value,
                    "acquired_price": i.average_acquired_price.value,
                    "acquired_value": i.acquired_value.value,
                    "performance": {
                        "percent": i.last_trading_day_performance.relative.value,
                        "value": i.last_trading_day_performance.absolute.value,
                    },
                },
            )
            for i in positions
        ]
