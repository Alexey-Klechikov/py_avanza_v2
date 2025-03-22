import pandas as pd

from services.ta.indicators.models.indicator import Indicator
from utils.logger.operators import get_logger

log = get_logger()


class IndicatorsCategoryBase:
    def __init__(self, data: pd.DataFrame) -> None:
        self.data = data
        self.indicators: dict[str, Indicator] = {}
