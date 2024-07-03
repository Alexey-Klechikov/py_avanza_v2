from typing import Dict

import pandas as pd

from services.ta.indicators.models import Indicator
from utils.logger import get_logger

log = get_logger()


class IndicatorsCategoryBase:
    def __init__(self, data: pd.DataFrame) -> None:
        self.data = data
        self.indicators: Dict[str, Indicator] = {}
