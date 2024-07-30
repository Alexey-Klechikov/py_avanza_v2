from typing import List, Optional

from avanza.constants import InstrumentType

from apis.avanza.client import get_client
from apis.avanza.operators.models import Position
from data.settings import ACCOUNT_ID
from utils.logger import get_logger

log = get_logger()


class AcquiredInstrument:
    def __init__(self):
        self.BULL: Optional[Position] = None
        self.BEAR: Optional[Position] = None


class Portfolio:
    def __init__(self):
        self.acquired_instrument: AcquiredInstrument = AcquiredInstrument()
        self.total_value = 0
        self.buying_power = 0
        self.positions: List[Position] = []
        self._account_url_parameter: Optional[str] = None

    def reload_balance(self) -> None:
        log.debug("Reload account balance")

        if not self._account_url_parameter:
            self.reload_positions()

        account_overview = get_client().get_accounts_overview(self._account_url_parameter)

        self.total_value = account_overview.total_value.total_value.value
        self.buying_power = account_overview.buying_power.total.value

    def reload_positions(self) -> None:
        positions = get_client().get_accounts_positions()

        self._account_url_parameter = [
            i.account.url_parameter_id for i in positions.cash_positions if i.account.id == ACCOUNT_ID
        ][0]

        self.positions = [
            Position(
                **{
                    "instrument": {
                        "id": i.instrument.orderbook.id,
                        "type": InstrumentType[i.instrument.type],
                        "name": i.instrument.name,
                    },
                    "quote": {
                        "buy": (None if not i.instrument.orderbook.quote.buy else i.instrument.orderbook.quote.buy.value),
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
            for i in positions.with_orderbook
            if i.account.id == ACCOUNT_ID
        ]

        if self.positions:
            log.debug("Active positions found")

    def detect_acquired_instruments(self) -> None:
        self.acquired_instrument = AcquiredInstrument()

        for position in self.positions:
            if position.instrument.type not in [
                InstrumentType.WARRANT,
                InstrumentType.CERTIFICATE,
            ]:
                continue

            instrument_direction = None

            if "BULL " in position.instrument.name or " L " in position.instrument.name:
                instrument_direction = "BULL"
            elif "BEAR " in position.instrument.name or " S " in position.instrument.name:
                instrument_direction = "BEAR"
            elif position.quote.sell is not None:
                instrument_direction = (
                    "BULL"
                    if (position.quote.sell > position.acquired_price and position.performance.percent > 0)
                    else "BEAR"
                )

            if not instrument_direction:
                raise ValueError(f"Unknown instrument direction for {position.instrument.name}")

            self.acquired_instrument.__setattr__(instrument_direction, position)
