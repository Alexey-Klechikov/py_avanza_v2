from dataclasses import dataclass

from apis.avanza.client.client import get_client
from apis.avanza.client.models.account.watchlists import Watchlist
from apis.avanza.client.models.instrument.certificate import InstrumentCertificate
from apis.avanza.client.models.instrument.warrant import InstrumentWarrant
from apis.avanza.operators.models.watchlist import Orderbook, PreferredInstrument, ValidInstruments
from config import SETTINGS
from utils.logger.operators import get_logger

log = get_logger()

INSTRUMENT_DIRECTIONS = {
    "Kort": "BEAR",
    "Lång": "BULL",
}

TRADING_PERSPECTIVE_PREFIX = "DT"
WATCHLIST_NAME_PARTS = 4

# Leverage tolerance constants
LEVERAGE_LOWER_MULTIPLIER = 0.85
LEVERAGE_UPPER_MULTIPLIER = 1.15

# Price and spread constants
MIN_SPREAD_PERCENT = 0.1
MIN_PRICE = 1
MAX_PRICE = 300

# Search prefix constants
WARRANT_BULL_PREFIX = "L"
WARRANT_BEAR_PREFIX = "S"


@dataclass
class UnpackedWatchlistName:
    trading_perspective: str = ""
    direction: str = ""
    instrument: str = ""
    instrument_type: str = ""

    @classmethod
    def from_name(cls, name: str) -> "UnpackedWatchlistName":
        """Parse a watchlist name into its components.
        Expected format: DT_<direction>_<instrument>_<instrument_type>
        """
        if not name.startswith(TRADING_PERSPECTIVE_PREFIX):
            return cls()

        parts = name.split("_")
        if len(parts) != WATCHLIST_NAME_PARTS:
            return cls()

        return cls(
            trading_perspective=parts[0],
            direction=parts[1],
            instrument=parts[2],
            instrument_type=parts[3],
        )

    def matches_filter(
        self,
        watchlist_name: str,
        filter_orderbook_type: str | None,
    ) -> bool:
        """Determine if a watchlist should be processed."""
        if not bool(self.trading_perspective):
            return False

        if self.trading_perspective != TRADING_PERSPECTIVE_PREFIX:
            return False

        if self.instrument != SETTINGS.NAME:
            return False

        if filter_orderbook_type and filter_orderbook_type not in watchlist_name:
            return False

        return True


class InstrumentValidators:
    @staticmethod
    def leverage_within_range(leverage: float) -> bool:
        return (
            SETTINGS.MULTIPLIER * LEVERAGE_LOWER_MULTIPLIER
            <= leverage
            <= SETTINGS.MULTIPLIER * LEVERAGE_UPPER_MULTIPLIER
        )

    @staticmethod
    def price_is_valid(spread: float | None, last_price: float | None) -> bool:
        if not spread or not last_price:
            return False

        return (
            spread > MIN_SPREAD_PERCENT
            and spread < SETTINGS.MAX_SPREAD * 100
            and last_price > MIN_PRICE
            and last_price < MAX_PRICE
        )

    @staticmethod
    def type_is_valid(
        watchlist_name: UnpackedWatchlistName,
        instrument_info: InstrumentWarrant | InstrumentCertificate,
        watchlist: Watchlist,
    ) -> bool:
        if watchlist_name.instrument_type == instrument_info.type:
            return True

        log.error(
            "> Wrong instrument type in watchlist %s - %s (expected: %s, got: %s)",
            watchlist.name,
            instrument_info.name,
            watchlist_name.instrument_type,
            instrument_info.type,
        )
        return False

    @staticmethod
    def direction_is_valid(
        watchlist_name: UnpackedWatchlistName,
        instrument_info: InstrumentWarrant | InstrumentCertificate,
        instrument_direction: str,
        watchlist: Watchlist,
    ) -> bool:
        if watchlist_name.direction == instrument_direction:
            return True

        log.error(
            "> Wrong instrument direction in watchlist %s - %s (expected: %s, got: %s)",
            watchlist.name,
            instrument_info.name,
            watchlist_name.direction,
            instrument_direction,
        )
        return False

    @staticmethod
    def market_maker_in_top_level(instrument_info: InstrumentWarrant | InstrumentCertificate) -> bool:
        if instrument_info.order_depth.market_maker_level_in_bid == 0:
            return True

        log.debug(
            "> Market maker in the order depth level: %s",
            instrument_info.order_depth.market_maker_level_in_bid,
        )
        return False


class Watchlists:
    def __init__(self, filter_orderbook_type: str | None = None) -> None:
        self.valid_instruments = ValidInstruments()
        self.preferred_instrument = PreferredInstrument()
        self.filter_orderbook_type = filter_orderbook_type

    def _set_preferred_instrument(self) -> None:
        """Set the preferred instrument for each direction based on leverage/spread ratio."""
        log.debug("Set preferred instruments using watchlists")
        for instrument_direction in INSTRUMENT_DIRECTIONS.values():
            instruments = self.valid_instruments.get(instrument_direction)
            if not instruments:
                continue

            preferred_instrument = max(
                instruments,
                key=lambda x: (x.leverage / x.spread) if x.leverage and x.spread else 0,
            )

            if preferred_instrument:
                self.preferred_instrument.set(instrument_direction, preferred_instrument)
                log.debug(
                    f"> Top instrument set: {preferred_instrument.name} [leverage {preferred_instrument.leverage}]",
                )

    def _process_certificate(self, orderbook_id: str) -> tuple[InstrumentCertificate, str]:
        """Process a certificate instrument and return info and direction."""
        instrument_info = get_client().get_instrument_certificate(orderbook_id)
        instrument_direction = INSTRUMENT_DIRECTIONS[instrument_info.direction]
        return instrument_info, instrument_direction

    def _process_warrant(self, orderbook_id: str) -> tuple[InstrumentWarrant, str] | tuple[None, None]:
        """Process a warrant instrument and return info and direction, or None if invalid leverage."""
        instrument_info = get_client().get_instrument_warrant(orderbook_id)
        instrument_direction = INSTRUMENT_DIRECTIONS[instrument_info.key_indicators.direction]

        if not InstrumentValidators.leverage_within_range(instrument_info.key_indicators.leverage):
            return None, None

        return instrument_info, instrument_direction

    def _refresh_one(self, watchlist: Watchlist, watchlist_name: UnpackedWatchlistName) -> None:
        """Process a single watchlist to extract valid instruments."""
        for orderbook_id in watchlist.orderbook_ids:
            # Get instrument info based on type
            if watchlist_name.instrument_type == "CERTIFICATE":
                instrument_info, instrument_direction = self._process_certificate(orderbook_id)
            elif watchlist_name.instrument_type == "WARRANT":
                instrument_info, instrument_direction = self._process_warrant(orderbook_id)
                if instrument_info is None or instrument_direction is None:
                    continue
            else:
                continue

            if not InstrumentValidators.type_is_valid(watchlist_name, instrument_info, watchlist):
                continue

            if not InstrumentValidators.direction_is_valid(
                watchlist_name,
                instrument_info,
                instrument_direction,
                watchlist,
            ):
                continue

            if not InstrumentValidators.market_maker_in_top_level(instrument_info):
                continue

            # Add to valid instruments
            self.valid_instruments.append(
                watchlist_name.direction,
                Orderbook(
                    id=orderbook_id,
                    name=instrument_info.name,
                    buy=instrument_info.quote.buy,
                    sell=instrument_info.quote.sell,
                    type=instrument_info.type,
                    spread=instrument_info.quote.spread,
                    leverage=instrument_info.key_indicators.leverage,
                    start_date=instrument_info.historical_closing_prices.start_date,
                ),
            )

    def _clear_one(self, watchlist: Watchlist) -> None:
        log.debug(f"Clear watchlist {watchlist.name}")

        for instrument_id in watchlist.orderbook_ids:
            get_client().remove_from_watchlist(instrument_id, watchlist.watchList_id)

    def _build_search_string(
        self,
        watchlist_name: UnpackedWatchlistName,
    ) -> str | None:
        """Build the search string based on instrument type."""
        if watchlist_name.instrument_type == "CERTIFICATE":
            return f"{watchlist_name.direction} {SETTINGS.NAME} AVA X{SETTINGS.MULTIPLIER}"
        elif watchlist_name.instrument_type == "WARRANT":
            prefix = WARRANT_BULL_PREFIX if watchlist_name.direction == "BULL" else WARRANT_BEAR_PREFIX
            return f"{prefix} {SETTINGS.NAME} AVA"
        return None

    def _update_one(self, watchlist: Watchlist, watchlist_name: UnpackedWatchlistName) -> None:
        """Update a watchlist with matching instruments from search."""
        log.debug(f"Update watchlist {watchlist.name}")

        search_string = self._build_search_string(watchlist_name)
        if not search_string:
            return

        search_result = get_client().filtered_search(search_string, [watchlist_name.instrument_type])

        if search_result.total_number_of_hits == 0:
            log.error(
                f"> Failed to find {watchlist_name.instrument_type} instruments using '{search_string}'",
            )
            return

        for hit in search_result.hits:
            if not InstrumentValidators.price_is_valid(hit.price.spread, hit.price.last):
                continue

            # Additional validation for warrants
            if watchlist_name.instrument_type == "WARRANT":
                instrument_info = get_client().get_instrument_warrant(hit.order_book_id)
                if not InstrumentValidators.leverage_within_range(instrument_info.key_indicators.leverage):
                    continue

            log.debug(f"> Add orderbook '{hit.title}' [Spread {hit.price.spread}%. Last price {hit.price.last}]")
            get_client().add_to_watchlist(hit.order_book_id, watchlist.watchList_id)

    def refresh_all(self) -> None:
        """Refresh all relevant watchlists and set preferred instruments."""
        log.debug("Refresh watchlists")

        self.valid_instruments = ValidInstruments()

        for watchlist in get_client().get_watchlists():
            unpacked_watchlist_name = UnpackedWatchlistName.from_name(watchlist.name)

            if not unpacked_watchlist_name.matches_filter(watchlist.name, self.filter_orderbook_type):
                continue

            self._refresh_one(watchlist, unpacked_watchlist_name)

        self._set_preferred_instrument()

    def update_all(self) -> None:
        log.info("Update watchlists")

        for watchlist in get_client().get_watchlists():
            unpacked_watchlist_name = UnpackedWatchlistName.from_name(watchlist.name)

            if not unpacked_watchlist_name.matches_filter(watchlist.name, self.filter_orderbook_type):
                continue

            if unpacked_watchlist_name.trading_perspective != TRADING_PERSPECTIVE_PREFIX:
                continue

            if unpacked_watchlist_name.instrument != SETTINGS.NAME:
                continue

            self._clear_one(watchlist)
            self._update_one(watchlist, unpacked_watchlist_name)
