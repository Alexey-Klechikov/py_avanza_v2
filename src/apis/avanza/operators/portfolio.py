from avanza.constants import InstrumentType

from apis.avanza.client.client import get_client
from apis.avanza.client.models.account.positions import WithOrderbookPosition
from apis.avanza.operators.models.position import Position
from config import SETTINGS
from utils.logger.operators import get_logger

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


def _to_position(account_position: WithOrderbookPosition) -> Position:
    quote = account_position.instrument.orderbook.quote
    performance = account_position.last_trading_day_performance

    return Position(
        **{
            "instrument": {
                "id": account_position.instrument.orderbook.id,
                "type": InstrumentType[account_position.instrument.type],
                "name": account_position.instrument.name,
            },
            "quote": {
                "buy": quote.buy.value if quote.buy else None,
                "sell": quote.sell.value if quote.sell else None,
            },
            "volume": account_position.volume.value,
            "value": account_position.value.value,
            "acquired_price": account_position.average_acquired_price.value,
            "acquired_value": account_position.acquired_value.value,
            "performance": {
                "percent": performance.relative.value if performance else None,
                "value": performance.absolute.value if performance else None,
            },
        },
    )


class Portfolio:
    def __init__(self):
        self.acquired_instrument: AcquiredInstrument = AcquiredInstrument()
        self.total_value = 0
        self.buying_power = 0
        self.positions: list[Position] = []

        self._account_url_parameter: str = self._get_account_url_parameter()

    def _get_account_url_parameter(self) -> str:
        account_url_parameter = next(
            (
                cash_position.account.url_parameter_id
                for cash_position in get_client().get_accounts_positions().cash_positions
                if cash_position.account.id == SETTINGS.ACCOUNT_ID
            ),
            None,
        )
        if account_url_parameter is None:
            raise ValueError(f"Account {SETTINGS.ACCOUNT_ID} (SETTINGS.ACCOUNT_ID) not found among Avanza accounts")

        return account_url_parameter

    def _detect_acquired_instruments(self) -> None:
        self.acquired_instrument = AcquiredInstrument()

        for position in self.positions:
            if position.instrument.type not in (InstrumentType.WARRANT, InstrumentType.CERTIFICATE):
                continue

            instrument_name = position.instrument.name
            if "BULL " in instrument_name or " L " in instrument_name:
                self.acquired_instrument.BULL = position
            elif "BEAR " in instrument_name or " S " in instrument_name:
                self.acquired_instrument.BEAR = position
            else:
                raise ValueError(f"Unknown instrument direction for {instrument_name}")

    def reload_balance(self) -> None:
        account_overview = get_client().get_accounts_overview(self._account_url_parameter)  # type: ignore

        self.total_value = round(account_overview.total_value.total_value.value)
        self.buying_power = round(account_overview.buying_power.total.value)

        log.debug(f"Reload account balance: total value {self.total_value}, buying power {self.buying_power}")

    def reload_positions(self, caller: str = "") -> None:
        self.positions = [
            _to_position(account_position)
            for account_position in get_client().get_accounts_positions().with_orderbook
            if account_position.account.id == SETTINGS.ACCOUNT_ID
            and SETTINGS.PRODUCT_NAME in account_position.instrument.name
        ]

        self._detect_acquired_instruments()

        if self.positions:
            log.debug("Active positions found [%d st.]%s", len(self.positions), f" [{caller}]" if caller else "")
