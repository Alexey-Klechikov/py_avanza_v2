from unittest import TestCase

from services.ta.strategies.models.signal import Signal


class Test_SignalFromBar(TestCase):
    def test_entries(self):
        assert Signal.from_bar(long=True, short=False) == Signal.LONG
        assert Signal.from_bar(long=False, short=True) == Signal.SHORT

    def test_conflicting_or_missing_entries_give_no_signal(self):
        assert Signal.from_bar(long=True, short=True) is None
        assert Signal.from_bar(long=False, short=False) is None
