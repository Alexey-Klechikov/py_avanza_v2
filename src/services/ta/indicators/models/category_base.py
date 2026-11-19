import pandas as pd
import pandas_ta as ta  # pylint: disable=unused-import # noqa: F401  (registers the DataFrame.ta accessor)

from services.ta.indicators.models.indicator import Indicator


class IndicatorsCategoryBase:
    def __init__(self, bars: pd.DataFrame) -> None:
        self.bars = bars
        self.indicators: dict[str, Indicator] = {}

    def _add_divergence_slopes(self, column: str, slope_column: str, length: int) -> str:
        """Add the linear-regression slopes of `column` (as `slope_column`) and of Close over `length` bars, which
        divergence rules compare; return the Close slope column."""
        close_slope_column = f"Close_slope_{length}"
        self.bars[close_slope_column] = self.bars.ta.linreg(length=length, slope=True)
        self.bars[slope_column] = self.bars.ta.linreg(close=column, length=length, slope=True)

        return close_slope_column
