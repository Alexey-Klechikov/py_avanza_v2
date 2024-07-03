from typing import Dict

import pandas_ta as ta  # type: ignore

from services.ta.indicators.models import HorizontalLine, Indicator, IndicatorsCategoryBase, Panel, Plot, Plots, Signal
from utils.logger import get_logger

log = get_logger()


class Cycles(IndicatorsCategoryBase):
    def _add_even_better_sinewave(self, length: int, bars: int) -> None:
        """
        EBSW (Even Better Sinewave)
        https://www.prorealcode.com/prorealtime-indicators/even-better-sinewave/
        """

        column_name = f"EBSW_{length}_{bars}"

        self.data.ta.ebsw(length=length, bars=bars, append=True)
        if column_name not in self.data.columns:
            log.debug("Indicator 'Cycles -> EBSW' can not be added.")
            return

        self._indicators["EBSW"] = Indicator(
            signal=Signal(
                BUY=lambda x: x[column_name] > 0.5,
                SELL=lambda x: x[column_name] < -0.5,
            ),
            columns=[column_name],
            plots=Plots(
                panel=Panel.SEPARATE,
                list=[
                    Plot(column=column_name, color="orange", ylim=[-1.1, 1.1], ylabel="Cycles [EBSW]"),
                ],
                horizontal_lines=[
                    HorizontalLine(y=0.5, color="red"),
                    HorizontalLine(y=-0.5, color="blue"),
                ],
            ),
        )

    def get(self) -> Dict:
        self._add_even_better_sinewave(length=40, bars=10)

        return super().get()
