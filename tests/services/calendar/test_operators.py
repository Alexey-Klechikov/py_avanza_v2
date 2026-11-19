from unittest import TestCase
from unittest.mock import patch

import pandas as pd

from services.calendar import operators


class Test_IsMarketClosed(TestCase):
    def test_a_day_without_an_nyse_session_is_closed(self):
        with patch.object(operators, "_today_nyse_schedule", return_value=pd.DataFrame()):
            assert operators.is_market_closed()


class Test_TradingEndTime(TestCase):
    def test_a_day_without_an_nyse_session_ends_at_once(self):
        from datetime import time

        with patch.object(operators, "_today_nyse_schedule", return_value=pd.DataFrame()):
            assert operators.get_trading_end_time() == time.min
