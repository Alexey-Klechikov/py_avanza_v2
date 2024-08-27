from avanza.models import WatchList

from apis.avanza.client import get_client
from apis.avanza.operators.models import Orderbook, PreferredInstrument, ValidInstruments
from utils.logger import get_logger

log = get_logger()


INSTRUMENT_DIRECTIONS = {
    "Kort": "BEAR",
    "Lång": "BULL",
}


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

    def _refresh_watchlist(self, watchlist: WatchList):
        watchlist_instrument_direction, watchlist_instrument, watchlist_instrument_type = watchlist.name.split("_")[1:]

        for orderbook_id in watchlist.orderbooks:
            if watchlist_instrument_type == "CERTIFICATE":
                instrument_info = get_client().get_instrument_certificate(orderbook_id)
                instrument_direction = INSTRUMENT_DIRECTIONS[instrument_info.direction]

            elif watchlist_instrument_type == "WARRANT":
                instrument_info = get_client().get_instrument_warrant(orderbook_id)
                instrument_direction = INSTRUMENT_DIRECTIONS[instrument_info.key_indicators.direction]
                if (
                    instrument_info.key_indicators.leverage < self.settings.MULTIPLIER * 0.75
                    or instrument_info.key_indicators.leverage > self.settings.MULTIPLIER * 1.35
                ):
                    continue
            else:
                continue

            if (watchlist_instrument_type.upper() != instrument_info.type) or (
                watchlist_instrument_direction != instrument_direction
            ):
                log.error(
                    "> Wrong instrument in the watchlist %s - %s",
                    watchlist.name,
                    instrument_info.name,
                )
                continue

            self.valid_instruments.__getattribute__(watchlist_instrument_direction).append(
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
        # Watchlist name is expected as "DT_{direction}_{type}"

        log.debug("Refresh watchlists")

        self.valid_instruments = ValidInstruments()

        for watchlist in get_client().get_watchlists():
            if not watchlist.name.startswith("DT"):
                continue

            self._refresh_watchlist(watchlist)

        self._set_preferred_instrument()

    def _clear_watchlist(self, watchlist: WatchList):
        log.debug(f"Clear watchlist {watchlist.name}")

        for instrument_id in watchlist.orderbooks:
            get_client().remove_from_watchlist(instrument_id, watchlist.id)

    def _update_watchlist(self, watchlist: WatchList):
        log.debug(f"Update watchlist {watchlist.name}")

        instrument_direction, instrument, instrument_type = watchlist.name.split("_")[1:]

        if instrument_type == "CERTIFICATE":
            search_string = f"{instrument_direction} OMX AVA X{self.settings.MULTIPLIER}"
        elif instrument_type == "WARRANT":
            search_string = f"{'L' if instrument_direction == 'BULL' else 'S'} OMX AVA"
        else:
            return

        search_result = get_client().search_instrument(search_string, [instrument_type])

        if search_result.total_number_of_hits == 0:
            log.error(
                f"> Failed to find {instrument_type} instruments using '{search_string}'",
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
            if not watchlist.name.startswith("DT"):
                continue

            self._clear_watchlist(watchlist)
            self._update_watchlist(watchlist)
