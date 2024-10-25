from avanza.constants import InstrumentType

from apis.avanza.client import get_client
from apis.avanza.operators.models import Position
from utils.logger import get_logger

log = get_logger()


class AcquiredInstrument:
    def __init__(self):
        self.BULL: Position | None = None
        self.BEAR: Position | None = None

    def get(self, direction: str) -> Position | None:
        if direction == "BULL":
            return self.BULL
        elif direction == "BEAR":
            return self.BEAR
        else:
            raise ValueError(f"Unknown instrument direction {direction}")


class Portfolio:
    def __init__(
        self,
        account_id: str,
        filter_orderbook_name: str | None = None,
        filter_orderbook_direction: str | None = None,
    ):
        self.acquired_instrument: AcquiredInstrument = AcquiredInstrument()
        self.total_value = 0
        self.buying_power = 0
        self.positions: list[Position] = []

        self.account_id = account_id
        self.filter_orderbook_name = filter_orderbook_name
        self.filter_orderbook_direction = filter_orderbook_direction

        self._account_url_parameter: str = self._get_account_url_parameter()

    def _get_account_url_parameter(self) -> str:
        return [
            i.account.url_parameter_id
            for i in get_client().get_accounts_positions().cash_positions
            if i.account.id == self.account_id
        ][0]

    def _detect_acquired_instruments(self) -> None:
        self.acquired_instrument = AcquiredInstrument()

        for position in self.positions:
            if position.instrument.type not in [
                InstrumentType.WARRANT,
                InstrumentType.CERTIFICATE,
            ]:
                continue

            if "BULL " in position.instrument.name or " L " in position.instrument.name:
                self.acquired_instrument.BULL = position
            elif "BEAR " in position.instrument.name or " S " in position.instrument.name:
                self.acquired_instrument.BEAR = position
            else:
                raise ValueError(f"Unknown instrument direction for {position.instrument.name}")

    def reload_balance(self) -> None:
        account_overview = get_client().get_accounts_overview(self._account_url_parameter)  # type: ignore

        self.total_value = round(account_overview.total_value.total_value.value)
        self.buying_power = round(account_overview.buying_power.total.value)

        log.debug(f"Reload account balance: total value {self.total_value}, buying power {self.buying_power}")

    def reload_positions(self, caller: str = "") -> None:
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
                        "percent": (
                            None if not i.last_trading_day_performance else i.last_trading_day_performance.relative.value
                        ),
                        "value": (
                            None if not i.last_trading_day_performance else i.last_trading_day_performance.absolute.value
                        ),
                    },
                },
            )
            for i in get_client().get_accounts_positions().with_orderbook
            if i.account.id == self.account_id
            and (not self.filter_orderbook_name or self.filter_orderbook_name in i.instrument.name)
            and (not self.filter_orderbook_direction or self.filter_orderbook_direction in i.instrument.name)
        ]

        self._detect_acquired_instruments()

        if self.positions:
            log.debug(f"Active positions found [{len(self.positions)} st.]" + (f" [caller {caller}]" if caller else ""))
