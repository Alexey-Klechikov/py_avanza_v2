from typing import List

from avanza.constants import InstrumentType

from apis.avanza.client import get_client
from apis.avanza.operators.models import Position
from data.settings import ACCOUNT_ID
from utils.logger import get_logger

log = get_logger()


class Portfolio:
    def __init__(self):
        self.total_value = 0
        self.buying_power = 0
        self.positions: List[Position] = []

    def refresh_balance(self) -> None:
        log.debug("Refresh account balance")

        accounts_overview = get_client().get_accounts_overview()

        account_overview = [i for i in accounts_overview.accounts if i.info.id == ACCOUNT_ID][0]

        self.total_value = account_overview.total_value.total_value.value
        self.buying_power = account_overview.buying_power.total.value

    def refresh_positions(self) -> None:
        log.debug("Refresh account positions")

        positions = get_client().get_accounts_positions().with_orderbook
        positions = [i for i in positions if i.account.id == ACCOUNT_ID]

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
