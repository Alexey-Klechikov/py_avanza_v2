import os
import pickle

import pandas as pd

from config import DATA_COLUMNS, SETTINGS
from utils.logger.operators import get_logger

log = get_logger()

SRC_DIR = os.path.abspath(os.path.join(__file__, "..", "..", ".."))


class Storage:
    def __init__(self, resolution: str = SETTINGS.RESOLUTION) -> None:
        self.path = f"{SRC_DIR}/data/{SETTINGS.NAME}_{resolution}.pickle"

    def read(self) -> pd.DataFrame:
        if not os.path.exists(self.path):
            log.warning(f"File does not exist: {self.path}")
            return pd.DataFrame(columns=DATA_COLUMNS)

        with open(self.path, "rb") as cache_file:
            return pickle.load(cache_file)

    def write(self, bars: pd.DataFrame) -> None:
        """Merge `bars` into the cache. For a timestamp present in both, the new row wins: a candle fetched while
        still in progress is replaced once it is fetched complete (its volume keeps growing until then)."""
        new_bars = bars[DATA_COLUMNS].dropna(how="any")
        if new_bars.empty:
            log.warning("Data is empty. Nothing to write.")
            return

        cached_bars = self.read()
        merged_bars = new_bars if cached_bars.empty else pd.concat([cached_bars[DATA_COLUMNS], new_bars])
        merged_bars = merged_bars[~merged_bars.index.duplicated(keep="last")].sort_index()
        merged_bars.index.name = "Datetime"

        with open(self.path, "wb") as cache_file:
            pickle.dump(merged_bars, cache_file)
