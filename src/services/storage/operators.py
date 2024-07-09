import os
import pickle
import re

import pandas as pd

from data.settings import DATA_COLUMNS
from utils.logger import get_logger

log = get_logger()


class Storage:
    def __init__(self, ticker_name: str, resolution: str) -> None:  # TODO: make resolution enum
        self.ticker_name = ticker_name
        self.resolution = resolution

        self.path = self._get_path()

    def _get_path(self) -> str:
        project_root_dir = os.path.abspath(os.path.join(__file__, "..", "..", ".."))
        file_name = re.sub(r"\W+", "", f"{self.ticker_name}_{self.resolution}")

        return f"{project_root_dir}/data/{file_name}.pickle"

    def _clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        data.loc[data.between_time("09:00", "09:05").index, "Volume"] = 0
        return data.between_time("09:00", "17:20")[DATA_COLUMNS].fillna(0)

    def read(self):
        if not os.path.exists(self.path):
            log.warning(f"File does not exist: {self.path}")
            return pd.DataFrame(columns=DATA_COLUMNS)

        with open(self.path, "rb") as f:
            return pickle.load(f)

    def write(self, data: pd.DataFrame) -> None:
        new_data = self._clean_data(data)
        if new_data.empty:
            log.warning("Data is empty. Nothing to write.")
            return

        old_data = self.read()

        if old_data.empty:
            combined_data = new_data
        else:
            combined_data = pd.concat([old_data, new_data]).reset_index()
            combined_data = (
                combined_data.loc[combined_data.groupby("Datetime")["Volume"].idxmax()].set_index("Datetime").sort_index()
            )

        with open(self.path, "wb") as f:
            pickle.dump(self._clean_data(combined_data), f)
