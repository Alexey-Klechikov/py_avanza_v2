from apis.avanza.client import get_client
from apis.avanza.client.models import InstrumentCertificate, InstrumentWarrant
from utils.logger import get_logger

log = get_logger()


class Instrument:
    def __init__(self, id: str, type: str):
        self.id: str = id
        self.type: str = type

    def _get_info(self) -> InstrumentCertificate | InstrumentWarrant | None:
        instrument_info = None

        if self.type == "CERTIFICATE":
            return get_client().get_instrument_certificate(self.id)

        elif self.type == "WARRANT":
            return get_client().get_instrument_warrant(self.id)

        if not instrument_info:
            log.error(f"Failed to get price for {self.id}")
            return

        return instrument_info

    def get_buy_price(self) -> float | None:
        instrument_info = self._get_info()

        if not instrument_info:
            return

        if instrument_info.order_depth.market_maker_level_in_bid != 0:
            log.info("> Market maker in the order depth level: %s", instrument_info.order_depth.market_maker_level_in_bid)
            return

        return instrument_info.quote.buy

    def get_sell_price(self) -> float | None:
        instrument_info = self._get_info()

        if not instrument_info:
            return

        return instrument_info.quote.sell
