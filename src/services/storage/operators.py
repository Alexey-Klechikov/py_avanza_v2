import os
import pickle

import pandas as pd

from config import DATA_COLUMNS, SETTINGS
from utils.logger.operators import get_logger

log = get_logger()


class Storage:
    def __init__(self, resolution: str = SETTINGS.RESOLUTION) -> None:
        self.resolution = resolution

        self.path = self._get_path()

    def _get_path(self) -> str:
        project_root_dir = os.path.abspath(os.path.join(__file__, "..", "..", ".."))

        return f"{project_root_dir}/data/{SETTINGS.NAME}_{self.resolution}.pickle"

    def read(self) -> pd.DataFrame:
        if not os.path.exists(self.path):
            log.warning(f"File does not exist: {self.path}")
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

        with open(self.path, "rb") as f:
            return pickle.load(f)

    def write(self, data: pd.DataFrame) -> None:
        """Merge `data` into the cache. For a timestamp present in both, the new row wins: a candle fetched while
        still in progress is replaced once it is fetched complete (index volume is always 0, so volume cannot
        tell the two apart)."""
        new_data = data[DATA_COLUMNS].dropna(how="any")
        if new_data.empty:
            log.warning("Data is empty. Nothing to write.")
            return

        old_data = self.read()
        combined_data = new_data if old_data.empty else pd.concat([old_data[DATA_COLUMNS], new_data])
        combined_data = combined_data[~combined_data.index.duplicated(keep="last")].sort_index()
        combined_data.index.name = "Datetime"

        with open(self.path, "wb") as f:
            pickle.dump(combined_data, f)
