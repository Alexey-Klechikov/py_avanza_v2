import os
import pickle
from typing import Optional

import pandas as pd

from config.settings import DATA_COLUMNS
from utils.logger import get_logger

log = get_logger()


class Storage:
    def __init__(self, settings, resolution: Optional[str] = None) -> None:
        self.file_prefix = settings.FILE_PREFIX
        self.resolution = resolution if resolution else settings.RESOLUTION

        self.path = self._get_path()

    def _get_path(self) -> str:
        project_root_dir = os.path.abspath(os.path.join(__file__, "..", "..", ".."))

        return f"{project_root_dir}/data/{self.file_prefix}_{self.resolution}.pickle"

    def read(self) -> pd.DataFrame:
        if not os.path.exists(self.path):
            log.warning(f"File does not exist: {self.path}")
            return pd.DataFrame(columns=DATA_COLUMNS)

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

        combined_data = combined_data[DATA_COLUMNS].dropna(how="any")

        with open(self.path, "wb") as f:
            pickle.dump(combined_data, f)
