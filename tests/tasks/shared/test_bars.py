from unittest import TestCase

import pandas as pd

from config import SETTINGS
from tasks.shared.bars import is_at_or_after_trading_end, is_in_trading_window


class Test_TradingWindow(TestCase):
    def test_bars_count_by_their_end_like_the_live_loop(self):
        starts = pd.DatetimeIndex(["2026-11-18 16:12", "2026-11-18 16:14", "2026-11-18 21:42", "2026-11-18 21:44"])
        assert (SETTINGS.TIME.START.strftime("%H:%M"), SETTINGS.TIME.END.strftime("%H:%M")) == ("16:15", "21:45")

        # 16:12 closes at 16:14 (before START); 21:44 closes at 21:46, the first close at or after END
        assert is_in_trading_window(starts).tolist() == [False, True, True, False]
        assert is_at_or_after_trading_end(starts).tolist() == [False, False, False, True]
