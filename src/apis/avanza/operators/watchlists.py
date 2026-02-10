from apis.avanza.client.client import get_client
from apis.avanza.client.models.account.watchlists import Watchlist
from apis.avanza.operators.models.watchlist import (
    InstrumentValidators,
    Orderbook,
    PreferredInstrument,
    UnpackedWatchlistName,
    ValidInstruments,
)
from config import SETTINGS, SETTINGS_WATCHLIST
from utils.logger.operators import get_logger

log = get_logger()


class Watchlists:
    def __init__(self, filter_orderbook_type: str | None = None) -> None:
        self.valid_instruments = ValidInstruments()
        self.preferred_instrument = PreferredInstrument()
        self.filter_orderbook_type = filter_orderbook_type

    def _set_preferred_instrument(self) -> None:
        log.debug("Set preferred instruments using watchlists")
        for instrument_direction in SETTINGS_WATCHLIST.INSTRUMENT_DIRECTIONS.values():
            instruments = self.valid_instruments.get(direction=instrument_direction)
            if not instruments:
                continue

            preferred_instrument = max(
                instruments,
                key=lambda x: (x.leverage / x.spread) if x.leverage and x.spread else 0,
            )

            if preferred_instrument:
                self.preferred_instrument.set(direction=instrument_direction, value=preferred_instrument)
                log.debug(
                    f"> Top instrument set: {preferred_instrument.name} [leverage {preferred_instrument.leverage}]",
                )

    def _refresh_one(self, watchlist: Watchlist, watchlist_name: UnpackedWatchlistName) -> None:
        for orderbook_id in watchlist.orderbook_ids:
            if watchlist_name.instrument_type == "CERTIFICATE":
                instrument_info = get_client().get_instrument_certificate(instrument_id=orderbook_id)
                instrument_direction = SETTINGS_WATCHLIST.INSTRUMENT_DIRECTIONS[instrument_info.direction]
                instrument_leverage = instrument_info.leverage
            elif watchlist_name.instrument_type == "WARRANT":
                instrument_info = get_client().get_instrument_warrant(instrument_id=orderbook_id)
                instrument_direction = SETTINGS_WATCHLIST.INSTRUMENT_DIRECTIONS[
                    instrument_info.key_indicators.direction
                ]
                instrument_leverage = instrument_info.key_indicators.leverage
            else:
                continue

            if not InstrumentValidators.leverage_within_range(leverage=instrument_leverage):
                continue

            if not InstrumentValidators.type_is_valid(
                watchlist_name=watchlist_name,
                instrument_info=instrument_info,
                watchlist=watchlist,
            ):
                continue

            if not InstrumentValidators.direction_is_valid(
                watchlist_name=watchlist_name,
                instrument_info=instrument_info,
                instrument_direction=instrument_direction,
                watchlist=watchlist,
            ):
                continue

            if not InstrumentValidators.market_maker_in_top_level(instrument_info=instrument_info):
                continue

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
            get_client().remove_from_watchlist(instrument_id=instrument_id, watchlist_id=watchlist.watchList_id)

    def _build_search_string(self, watchlist_name: UnpackedWatchlistName) -> str | None:
        if watchlist_name.instrument_type == "CERTIFICATE":
            return f"{watchlist_name.direction} {SETTINGS.NAME} AVA X{SETTINGS.MULTIPLIER}"

        elif watchlist_name.instrument_type == "WARRANT":
            prefix = SETTINGS_WATCHLIST.SEARCH_WARRANT_PREFIX[watchlist_name.direction]
            return f"{prefix} {SETTINGS.NAME} AVA"

        return None

    def _update_one(self, watchlist: Watchlist, watchlist_name: UnpackedWatchlistName) -> None:
        log.debug(f"Update watchlist {watchlist.name}")

        search_string = self._build_search_string(watchlist_name=watchlist_name)
        if not search_string:
            return

        search_result = get_client().filtered_search(
            search_string=search_string,
            types=[watchlist_name.instrument_type],
        )

        if search_result.total_number_of_hits == 0:
            log.error(
                f"> Failed to find {watchlist_name.instrument_type} instruments using '{search_string}'",
            )
            return

        for hit in search_result.hits:
            if not InstrumentValidators.price_is_valid(spread=hit.price.spread, last_price=hit.price.last):
                continue

            # Additional validation for warrants
            if watchlist_name.instrument_type == "WARRANT":
                instrument_info = get_client().get_instrument_warrant(instrument_id=hit.order_book_id)
                if not InstrumentValidators.leverage_within_range(leverage=instrument_info.key_indicators.leverage):
                    continue

            log.debug(f"> Add orderbook '{hit.title}' [Spread {hit.price.spread}%. Last price {hit.price.last}]")
            get_client().add_to_watchlist(instrument_id=hit.order_book_id, watchlist_id=watchlist.watchList_id)

    # Public methods

    def refresh_all(self) -> None:
        log.debug("Refresh watchlists")

        self.valid_instruments = ValidInstruments()

        for watchlist in get_client().get_watchlists():
            unpacked_watchlist_name = UnpackedWatchlistName.from_name(name=watchlist.name)

            if not unpacked_watchlist_name.matches_filter(
                watchlist_name=watchlist.name,
                filter_orderbook_type=self.filter_orderbook_type,
            ):
                continue

            self._refresh_one(watchlist=watchlist, watchlist_name=unpacked_watchlist_name)

        self._set_preferred_instrument()

    def update_all(self) -> None:
        log.info("Update watchlists")

        for watchlist in get_client().get_watchlists():
            unpacked_watchlist_name = UnpackedWatchlistName.from_name(name=watchlist.name)

            if not unpacked_watchlist_name.matches_filter(
                watchlist_name=watchlist.name,
                filter_orderbook_type=self.filter_orderbook_type,
            ):
                continue

            if unpacked_watchlist_name.trading_perspective != SETTINGS_WATCHLIST.TRADING_PERSPECTIVE_PREFIX:
                continue

            if unpacked_watchlist_name.instrument != SETTINGS.NAME:
                continue

            self._clear_one(watchlist=watchlist)
            self._update_one(watchlist=watchlist, watchlist_name=unpacked_watchlist_name)
