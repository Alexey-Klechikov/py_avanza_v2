import mplfinance as mpf
import pandas as pd

from services.ta.indicators.models.indicator import Panel, Plots
from utils.logger import get_logger

log = get_logger()


class Figure:
    def __init__(self, data: pd.DataFrame):
        self.data = data

        self._plots = []
        self._title = []
        self._count_panels = 1

    def add_plot(self, plot: Plots) -> None:
        if plot.panel == Panel.SEPARATE:
            self._count_panels += 1
        panel = 0 if plot.panel == Panel.MAIN else self._count_panels

        for p in plot.list:
            if p.ylabel:
                self._title.append(p.ylabel)
            self._plots.append(mpf.make_addplot(self.data[p.column], panel=panel, **p.get_kwargs()))

        for hl in plot.horizontal_lines:
            self.data[f"hline_{hl.y}"] = hl.y
            self._plots.append(
                mpf.make_addplot(self.data[f"hline_{hl.y}"], color=hl.color, secondary_y=False, panel=panel),
            )

    def show(self) -> None:
        fig, ax = mpf.plot(
            self.data,
            title=" | ".join(self._title),
            addplot=self._plots,
            type="candle",
            volume=True,
            style="yahoo",
            ylabel_lower="Volume",
            ylabel="Price",
            warn_too_much_data=9999,
            figsize=(18, 12),
            scale_padding={"left": 0.2, "top": 0.5, "right": 0.6, "bottom": 0.5},
            returnfig=True,
        )

        for i in range(0, len(ax)):
            for grid in ["major", "minor"]:
                ax[i].grid(which=grid, color="gray", linestyle="--", linewidth=1, alpha=0.7)

            for spine in ax[i].spines.values():
                spine.set_edgecolor("black")
                spine.set_linestyle("-")
                spine.set_linewidth(1)
                spine.set_alpha(1)

        mpf.show()
