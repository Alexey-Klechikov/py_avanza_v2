from avanza.models import WatchList

from apis.avanza.client import get_client
from apis.avanza.operators.models import Orderbook, PreferredInstrument, ValidInstruments
from utils.logger import get_logger

log = get_logger()


INSTRUMENT_DIRECTIONS = {
    "Kort": "BEAR",
    "Lång": "BULL",
}


class UnpackedWatchlistName:
    def __init__(self, name: str):
        self.trading_perspective = ""
        self.direction = ""
        self.instrument = ""
        self.instrument_type = ""

        if not name.startswith("DT") or not len(name.split("_")) == 4:
            return

        self.trading_perspective, self.direction, self.instrument, self.instrument_type = name.split("_")


class Watchlists:
    def __init__(self, settings):
        self.settings = settings
        self.valid_instruments = ValidInstruments()
        self.preferred_instrument = PreferredInstrument()

    def _set_preferred_instrument(self):
        log.info("Set preferred instruments using watchlists")
        for instrument_direction in INSTRUMENT_DIRECTIONS.values():
            if not self.valid_instruments.__getattribute__(instrument_direction):
                continue

            self.preferred_instrument.__setattr__(
                instrument_direction,
                max(
                    self.valid_instruments.__getattribute__(instrument_direction),
                    key=lambda x: (x.leverage / x.spread) if x.leverage and x.spread else 0,
                ),
            )

            log.info(
                f"> Top instrument set: {self.preferred_instrument.__getattribute__(instrument_direction).name}"
                + f" [leverage {self.preferred_instrument.__getattribute__(instrument_direction).leverage}]",
            )

    def _refresh_watchlist(self, watchlist: WatchList, watchlist_name: UnpackedWatchlistName):
        for orderbook_id in watchlist.orderbooks:
            if watchlist_name.instrument_type == "CERTIFICATE":
                instrument_info = get_client().get_instrument_certificate(orderbook_id)
                instrument_direction = INSTRUMENT_DIRECTIONS[instrument_info.direction]

            elif watchlist_name.instrument_type == "WARRANT":
                instrument_info = get_client().get_instrument_warrant(orderbook_id)
                instrument_direction = INSTRUMENT_DIRECTIONS[instrument_info.key_indicators.direction]
                if (
                    instrument_info.key_indicators.leverage < self.settings.MULTIPLIER * 0.75
                    or instrument_info.key_indicators.leverage > self.settings.MULTIPLIER * 1.35
                ):
                    continue
            else:
                continue

            if (watchlist_name.instrument_type != instrument_info.type) or (
                watchlist_name.direction != instrument_direction
            ):
                log.error(
                    "> Wrong instrument in the watchlist %s - %s",
                    watchlist.name,
                    instrument_info.name,
                )
                continue

            self.valid_instruments.__getattribute__(watchlist_name.direction).append(
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

    def refresh_watchlists(self):
        log.debug("Refresh watchlists")

        self.valid_instruments = ValidInstruments()

        for watchlist in get_client().get_watchlists():
            unpacked_watchlist_name = UnpackedWatchlistName(watchlist.name)
            if (
                unpacked_watchlist_name.trading_perspective != "DT"
                or unpacked_watchlist_name.instrument != self.settings.NAME
            ):
                continue

            self._refresh_watchlist(watchlist, unpacked_watchlist_name)

        self._set_preferred_instrument()

    def _clear_watchlist(self, watchlist: WatchList):
        log.debug(f"Clear watchlist {watchlist.name}")

        for instrument_id in watchlist.orderbooks:
            get_client().remove_from_watchlist(instrument_id, watchlist.id)

    def _update_watchlist(self, watchlist: WatchList, watchlist_name: UnpackedWatchlistName):
        log.debug(f"Update watchlist {watchlist.name}")

        if watchlist_name.instrument_type == "CERTIFICATE":
            search_string = f"{watchlist_name.direction} {self.settings.NAME} AVA X{self.settings.MULTIPLIER}"
        elif watchlist_name.instrument_type == "WARRANT":
            search_string = f"{'L' if watchlist_name.direction == 'BULL' else 'S'} {self.settings.NAME} AVA"
        else:
            return

        search_result = get_client().search_instrument(search_string, [watchlist_name.instrument_type])

        if search_result.total_number_of_hits == 0:
            log.error(
                f"> Failed to find {watchlist_name.instrument_type} instruments using '{search_string}'",
            )
            return

        for hit in search_result.hits:
            if (
                hit.price.today_change_percent != 0
                and hit.price.spread
                and hit.price.spread > 0.1
                and hit.price.spread < 1.5
                and hit.price.last
                and hit.price.last > 1
                and hit.price.last < 200
            ):
                log.debug(f"> Add orderbook '{hit.title}' [Spread {hit.price.spread}%. Last price {hit.price.last}]")

                get_client().add_to_watchlist(hit.order_book_id, watchlist.id)

    def update_watchlists(self):
        log.info("Update watchlists")

        for watchlist in get_client().get_watchlists():
            unpacked_watchlist_name = UnpackedWatchlistName(watchlist.name)
            if (
                unpacked_watchlist_name.trading_perspective != "DT"
                or unpacked_watchlist_name.instrument != self.settings.NAME
            ):
                continue

            self._clear_watchlist(
                watchlist,
            )
            self._update_watchlist(watchlist, unpacked_watchlist_name)
