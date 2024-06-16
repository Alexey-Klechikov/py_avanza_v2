from typing import Optional, Union

from avanza.constants import InstrumentType

from services.avanza.client import get_client
from services.avanza.client.models import InstrumentCertificate, InstrumentStock, InstrumentWarrant
from services.avanza.operators.models import InstrumentInfo
from utils.logger import get_logger

log = get_logger()


class Instrument:
    def __init__(self):
        self.active: Optional[InstrumentInfo] = None

    @classmethod
    def _get_market_maker_spread(cls, levels) -> Optional[float]:
        if not levels:
            return None

        buy_level = max(levels, key=lambda x: x.buy_side.volume)
        sell_level = min(levels, key=lambda x: x.sell_side.volume)

        return (
            None
            if not buy_level or not sell_level
            else round((sell_level.sell_side.price / buy_level.buy_side.price - 1) * 100, 2)
        )

    @classmethod
    def get(cls, instrument_id: str, instrument_type: Optional[InstrumentType] = None) -> Optional[InstrumentInfo]:
        for candidate_instrument_type, method_get_instrument in [
            (InstrumentType.CERTIFICATE, get_client().get_instrument_certificate),
            (InstrumentType.WARRANT, get_client().get_instrument_warrant),
            (InstrumentType.STOCK, get_client().get_instrument_stock),
        ]:
            if instrument_type and candidate_instrument_type != instrument_type:
                continue

            try:
                data: Union[InstrumentStock, InstrumentCertificate, InstrumentWarrant] = method_get_instrument(
                    instrument_id,
                )
                return InstrumentInfo(
                    **{
                        **data.order_depth.model_dump(),
                        **data.quote.model_dump(),
                        **{"spread_market_maker": cls._get_market_maker_spread(data.order_depth.levels)},
                    },
                )
            except Exception as e:
                log.error(f"Failed to get instrument {id} as {candidate_instrument_type}: {e}")
