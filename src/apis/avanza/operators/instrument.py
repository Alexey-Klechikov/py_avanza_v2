from apis.avanza.client.client import get_client
from apis.avanza.client.models.instrument.certificate import InstrumentCertificate
from apis.avanza.client.models.instrument.warrant import InstrumentWarrant
from utils.logger.operators import get_logger

log = get_logger()


class Instrument:
    def __init__(self, instrument_id: str, instrument_type: str):
        self.instrument_id = instrument_id
        self.instrument_type = instrument_type

    def _get_info(self) -> InstrumentCertificate | InstrumentWarrant | None:
        if self.instrument_type == "CERTIFICATE":
            return get_client().get_instrument_certificate(self.instrument_id)

        if self.instrument_type == "WARRANT":
            return get_client().get_instrument_warrant(self.instrument_id)

        log.error(f"Failed to get price for {self.instrument_id}")
        return None

    def get_buy_price(self) -> float | None:
        instrument_info = self._get_info()

        if not instrument_info:
            return

        if instrument_info.order_depth.market_maker_level_in_bid != 0:
            log.debug(
                "> Market maker in the order depth level: %s",
                instrument_info.order_depth.market_maker_level_in_bid,
            )
            return

        return instrument_info.quote.buy

    def get_sell_price(self) -> float | None:
        instrument_info = self._get_info()

        if not instrument_info:
            return

        return instrument_info.quote.sell
