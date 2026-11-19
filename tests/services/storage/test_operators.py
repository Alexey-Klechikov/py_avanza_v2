import os
import tempfile
from unittest import TestCase

import pandas as pd

from services.storage.operators import Storage


def _candles(rows: dict[str, tuple[float, float, float, float]]) -> pd.DataFrame:
    frame = pd.DataFrame.from_dict(rows, orient="index", columns=["Open", "High", "Low", "Close"])
    frame["Volume"] = 0
    frame.index = pd.to_datetime(frame.index)
    frame.index.name = "Datetime"
    return frame


class Test_StorageWrite(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.storage = Storage()
        self.storage.path = os.path.join(self.directory.name, "OMX_2m.pickle")

    def tearDown(self):
        self.directory.cleanup()

    def test_completed_candle_replaces_the_partial_one(self):
        self.storage.write(_candles({"2026-11-17 10:00": (100, 100.1, 100, 100.1)}))  # stored 6 s into the candle
        self.storage.write(
            _candles({"2026-11-17 10:00": (100, 101, 99, 100.5), "2026-11-17 10:02": (100.5, 100.6, 100.5, 100.6)}),
        )

        stored = self.storage.read()

        assert stored.loc["2026-11-17 10:00"].tolist() == [100, 101, 99, 100.5, 0]  # type: ignore
        assert len(stored) == 2 and stored.index.is_monotonic_increasing

    def test_rows_with_missing_prices_do_not_overwrite(self):
        self.storage.write(_candles({"2026-11-17 10:00": (100, 101, 99, 100.5)}))
        self.storage.write(_candles({"2026-11-17 10:00": (float("nan"), 101, 99, 100.5)}))

        assert self.storage.read().loc["2026-11-17 10:00", "Open"] == 100
