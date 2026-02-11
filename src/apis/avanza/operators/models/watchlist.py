from dataclasses import dataclass
from datetime import date

from pydantic import BaseModel, Field

from apis.avanza.client.models.account.watchlists import Watchlist
from apis.avanza.client.models.instrument.certificate import InstrumentCertificate
from apis.avanza.client.models.instrument.warrant import InstrumentWarrant
from config import SETTINGS, SETTINGS_WATCHLIST
from utils.logger.operators import get_logger

log = get_logger()


class Orderbook(BaseModel):
    id: str
    type: str
    name: str
    spread: float | None
    buy: float | None
    sell: float | None
    leverage: float
    start_date: date


class ValidInstruments(BaseModel):
    BULL: list[Orderbook] = Field(default_factory=list)
    BEAR: list[Orderbook] = Field(default_factory=list)

    def get(self, direction: str) -> list[Orderbook]:
        if direction == "BULL":
            return self.BULL
        elif direction == "BEAR":
            return self.BEAR
        else:
            raise ValueError(f"Unknown direction: {direction}")

    def set(self, direction: str, value: list[Orderbook]) -> None:
        if direction == "BULL":
            self.BULL = value
        elif direction == "BEAR":
            self.BEAR = value
        else:
            raise ValueError(f"Unknown direction: {direction}")

    def append(self, direction: str, value: Orderbook) -> None:
        if direction == "BULL":
            self.BULL.append(value)
        elif direction == "BEAR":
            self.BEAR.append(value)
        else:
            raise ValueError(f"Unknown direction: {direction}")


class PreferredInstrument(BaseModel):
    BULL: Orderbook | None = Field(default=None)
    BEAR: Orderbook | None = Field(default=None)

    def get(self, direction: str) -> Orderbook | None:
        if direction == "BULL":
            return self.BULL
        elif direction == "BEAR":
            return self.BEAR
        else:
            raise ValueError(f"Unknown direction: {direction}")

    def set(self, direction: str, value: Orderbook | None) -> None:
        if direction == "BULL":
            self.BULL = value
        elif direction == "BEAR":
            self.BEAR = value
        else:
            raise ValueError(f"Unknown direction: {direction}")


@dataclass
class WatchlistNameComposition:
    trading_perspective: str = ""
    direction: str = ""
    instrument: str = ""
    instrument_type: str = ""

    @classmethod
    def from_name(cls, name: str) -> "WatchlistNameComposition":
        """Parse a watchlist name into its components.
        Expected format: DT_<direction>_<instrument>_<instrument_type>
        """
        if not name.startswith(SETTINGS_WATCHLIST.TRADING_PERSPECTIVE_PREFIX):
            return cls()

        parts = name.split("_")
        if len(parts) != SETTINGS_WATCHLIST.WATCHLIST_NAME_PARTS:
            return cls()

        return cls(trading_perspective=parts[0], direction=parts[1], instrument=parts[2], instrument_type=parts[3])

    def is_valid(self) -> bool:
        if self.trading_perspective != SETTINGS_WATCHLIST.TRADING_PERSPECTIVE_PREFIX:
            return False

        if self.instrument != SETTINGS.NAME:
            return False

        return True


class InstrumentValidators:
    @staticmethod
    def leverage_within_range(leverage: float) -> bool:
        return (
            SETTINGS.MULTIPLIER * SETTINGS_WATCHLIST.LEVERAGE_LOWER_MULTIPLIER
            <= leverage
            <= SETTINGS.MULTIPLIER * SETTINGS_WATCHLIST.LEVERAGE_UPPER_MULTIPLIER
        )

    @staticmethod
    def price_is_valid(spread: float | None, last_price: float | None) -> bool:
        if not spread or not last_price:
            return False

        return (
            spread > SETTINGS_WATCHLIST.MIN_SPREAD_PERCENT
            and spread < SETTINGS.MAX_SPREAD * 100
            and last_price > SETTINGS_WATCHLIST.MIN_PRICE
            and last_price < SETTINGS_WATCHLIST.MAX_PRICE
        )

    @staticmethod
    def type_is_valid(
        watchlist_name_composition: WatchlistNameComposition,
        instrument_info: InstrumentWarrant | InstrumentCertificate,
        watchlist: Watchlist,
    ) -> bool:
        if watchlist_name_composition.instrument_type == instrument_info.type:
            return True

        log.error(
            "> Wrong instrument type in watchlist %s - %s (expected: %s, got: %s)",
            watchlist.name,
            instrument_info.name,
            watchlist_name_composition.instrument_type,
            instrument_info.type,
        )
        return False

    @staticmethod
    def direction_is_valid(
        watchlist_name_composition: WatchlistNameComposition,
        instrument_info: InstrumentWarrant | InstrumentCertificate,
        instrument_direction: str,
        watchlist: Watchlist,
    ) -> bool:
        if watchlist_name_composition.direction == instrument_direction:
            return True

        log.error(
            "> Wrong instrument direction in watchlist %s - %s (expected: %s, got: %s)",
            watchlist.name,
            instrument_info.name,
            watchlist_name_composition.direction,
            instrument_direction,
        )
        return False

    @staticmethod
    def market_maker_in_top_level(instrument_info: InstrumentWarrant | InstrumentCertificate) -> bool:
        if instrument_info.order_depth.market_maker_level_in_bid == 0:
            return True

        log.debug("> Market maker in the order depth level: %s", instrument_info.order_depth.market_maker_level_in_bid)
        return False
