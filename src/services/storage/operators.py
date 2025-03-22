import os
import pickle

import pandas as pd

from config import SETTINGS
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
        if data.empty:
            log.warning("Data is empty. Nothing to write.")
            return

        old_data = self.read()

        if old_data.empty:
            combined_data = data
        else:
            combined_data = pd.concat([old_data, data]).reset_index()
            combined_data = (
                combined_data.loc[combined_data.groupby("Datetime")["Volume"].idxmax()].set_index("Datetime").sort_index()
            )

        combined_data = combined_data[["Open", "High", "Low", "Close", "Volume"]].dropna(how="any")

        with open(self.path, "wb") as f:
            pickle.dump(combined_data, f)
