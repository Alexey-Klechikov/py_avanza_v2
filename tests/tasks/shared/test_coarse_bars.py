from unittest import TestCase

import pandas as pd

from tasks.shared.coarse_bars import completing_bars


class Test_CompletingBars(TestCase):
    def test_empty_history_has_no_complete_bars(self):
        empty = pd.DataFrame({"Close": []}, index=pd.DatetimeIndex([]))

        assert completing_bars(empty, pd.Timedelta("30min"), pd.Timedelta("2min")).empty
