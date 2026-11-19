from unittest import TestCase

from apis.avanza.operators.models.watchlist import WatchlistNameComposition
from apis.avanza.operators.watchlists import Watchlists


class Test_BuildSearchString(TestCase):
    def test_certificates_are_searched_by_avanza_product_name(self):
        watchlists = Watchlists()

        bull = WatchlistNameComposition.from_name("DT_BULL_TSLA_CERTIFICATE")
        bear = WatchlistNameComposition.from_name("DT_BEAR_TSLA_CERTIFICATE")

        assert watchlists._build_search_string(watchlist_name_composition=bull) == "BULL TESLA X10 AVA"
        assert watchlists._build_search_string(watchlist_name_composition=bear) == "BEAR TESLA X10 AVA"
