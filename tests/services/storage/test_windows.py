from datetime import datetime
from unittest import TestCase

import pandas as pd

from src.services.storage.windows import DataWindow

END = datetime(2026, 11, 21)


class Test_DataWindow(TestCase):
    def test_slice_is_half_open_copy(self):
        window = DataWindow.days_before(END, days=2)
        index = pd.to_datetime(["2026-11-18 23:59", "2026-11-19 00:00", "2026-11-20 17:00", "2026-11-21 00:00"])
        bars = pd.DataFrame({"Close": [1.0, 2.0, 3.0, 4.0]}, index=index)

        window_bars = window.slice(bars)
        window_bars["Close"] = 0.0

        assert window_bars.index.tolist() == index[1:3].tolist()
        assert bars["Close"].tolist() == [1.0, 2.0, 3.0, 4.0]
