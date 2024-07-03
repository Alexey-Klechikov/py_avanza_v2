from typing import List

import pandas as pd

from services.ta.figure import Figure
from services.ta.indicators import Cycles, Momentum, Overlap, Trend, Volatility, Volume
from services.ta.indicators.models import Plots


def get_indicators(data) -> dict:
    indicators = dict()

    for indicator_category in [
        Trend,
        Volatility,
        Volume,
        Cycles,
        Overlap,
        Momentum,
    ]:
        indicators[indicator_category.__name__] = indicator_category(data).get()

    return indicators


def plot_indicators(data: pd.DataFrame, indicators_plots: List[Plots]):
    figure = Figure(data=data)

    for plots in indicators_plots:
        figure.add_plot(plots)

    figure.show()
