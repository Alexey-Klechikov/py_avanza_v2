import pandas_ta as ta  # pylint: disable=unused-import # noqa: F401

from services.ta.indicators.models.category_base import IndicatorsCategoryBase
from services.ta.indicators.models.indicator import Indicator, IndicatorSignal
from utils.logger.operators import get_logger

log = get_logger()


class Cycles(IndicatorsCategoryBase):
    def add_even_better_sinewave(self, length: int, bars: int) -> None:
        """
        EBSW (Even Better Sinewave)
        https://www.prorealcode.com/prorealtime-indicators/even-better-sinewave/

        :param length: The length. Default is 40.

        This indicator measures market cycles and uses a low pass filter to remove noise.
        Its output is bound signal between -1 and 1 and the maximum length of a detected
        trend is limited by its length input.
        """
        column = f"EBSW_{length}_{bars}"

        self.bars.ta.ebsw(length=length, bars=bars, append=True)
        if column not in self.bars.columns:
            log.debug("Indicator 'Cycles -> EBSW' can not be added.")
            return

        self.indicators["EBSW"] = Indicator(
            signal=IndicatorSignal(LONG=lambda x: x[column] > 0.5, SHORT=lambda x: x[column] < -0.5),
            columns=[column],
        )
