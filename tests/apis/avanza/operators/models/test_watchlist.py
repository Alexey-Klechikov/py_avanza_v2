from datetime import date
from unittest import TestCase

from apis.avanza.operators.models.watchlist import Orderbook, PreferredInstrument, ValidInstruments


def _orderbook(orderbook_id: str) -> Orderbook:
    return Orderbook(
        id=orderbook_id,
        type="CERTIFICATE",
        name=f"BULL TSLA X5 AVA {orderbook_id}",
        spread=0.2,
        buy=10.0,
        sell=10.1,
        leverage=5.0,
        start_date=date(2026, 1, 1),
    )


class TestValidInstruments(TestCase):
    def test_append_and_get_by_direction(self):
        valid_instruments = ValidInstruments()

        valid_instruments.append("BULL", _orderbook("1"))

        self.assertEqual([orderbook.id for orderbook in valid_instruments.get("BULL")], ["1"])
        self.assertEqual(valid_instruments.get("BEAR"), [])

    def test_unknown_direction_raises(self):
        with self.assertRaises(ValueError):
            ValidInstruments().get("SIDEWAYS")

        with self.assertRaises(ValueError):
            ValidInstruments().append("SIDEWAYS", _orderbook("1"))


class TestPreferredInstrument(TestCase):
    def test_set_and_get_by_direction(self):
        preferred_instrument = PreferredInstrument()

        preferred_instrument.set("BEAR", _orderbook("2"))

        self.assertEqual(preferred_instrument.BEAR.id, "2")
        self.assertIsNone(preferred_instrument.get("BULL"))

    def test_unknown_direction_raises(self):
        with self.assertRaises(ValueError):
            PreferredInstrument().set("SIDEWAYS", None)

        with self.assertRaises(ValueError):
            PreferredInstrument().get("SIDEWAYS")
