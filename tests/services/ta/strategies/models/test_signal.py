from unittest import TestCase

from src.services.ta.strategies.models.signal import Signal


class Test_SignalFromBar(TestCase):
    def test_exit_wins_over_entries(self):
        assert Signal.from_bar(long=True, short=False, exit=True) == Signal.EXIT

    def test_entries(self):
        assert Signal.from_bar(long=True, short=False, exit=False) == Signal.LONG
        assert Signal.from_bar(long=False, short=True, exit=False) == Signal.SHORT

    def test_conflicting_or_missing_entries_give_no_signal(self):
        assert Signal.from_bar(long=True, short=True, exit=False) is None
        assert Signal.from_bar(long=False, short=False, exit=False) is None
