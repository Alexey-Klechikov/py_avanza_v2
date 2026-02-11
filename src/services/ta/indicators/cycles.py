import pandas_ta as ta  # noqa: F401

from services.ta.indicators.models.category_base import IndicatorsCategoryBase
from services.ta.indicators.models.indicator import HorizontalLine, Indicator, Panel, Plot, Plots, Signal
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

        column_name = f"EBSW_{length}_{bars}"

        self.data.ta.ebsw(length=length, bars=bars, append=True)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Cycles -> EBSW' can not be added.")
            return

        self.indicators["EBSW"] = Indicator(
            signal=Signal(LONG=lambda x: x[column_name] > 0.5, SHORT=lambda x: x[column_name] < -0.5),
            columns=[column_name],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[Plot(columns=[column_name], color="orange", ylim=[-1.1, 1.1], ylabel="Cycles [EBSW]")],
                horizontal_lines=[HorizontalLine(y=0.5, color="red"), HorizontalLine(y=-0.5, color="blue")],
            ),
        )
