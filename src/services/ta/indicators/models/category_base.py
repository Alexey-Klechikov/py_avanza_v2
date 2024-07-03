from typing import Dict

import pandas as pd

from data.settings import DATA_COLUMNS
from services.ta.indicators.models import Indicator
from utils.logger import get_logger

log = get_logger()


class IndicatorsCategoryBase:
    def __init__(self, data: pd.DataFrame) -> None:
        self.data = data
        self._columns_before = set(self.data.columns) | set(DATA_COLUMNS)
        self._indicators = dict()

    def get(self) -> Dict[str, Indicator]:
        columns_latest = set(self.data.columns)

        columns_needed = set()
        for indicator in self._indicators.values():
            columns_needed |= set(indicator.columns)

        self.data.drop(columns=list(columns_latest - self._columns_before - columns_needed), inplace=True)

        return self._indicators
