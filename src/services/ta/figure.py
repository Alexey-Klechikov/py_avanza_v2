import mplfinance as mpf
import pandas as pd
from matplotlib.ticker import MultipleLocator

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

            plot_kwargs = {**p.get_kwargs(), **{"panel": panel, "data": self.data[p.columns]}}
            if len(p.columns) >= 2:
                plot_kwargs.update(secondary_y=False)

            self._plots.append(mpf.make_addplot(**plot_kwargs))

        for hl in plot.horizontal_lines:
            self.data[f"hline_{hl.y}"] = hl.y
            self._plots.append(
                mpf.make_addplot(self.data[f"hline_{hl.y}"], color=hl.color, secondary_y=False, panel=panel),
            )

    def show(self) -> None:
        _, ax = mpf.plot(
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

        start_of_day_indices = self.data.index.to_series().groupby(self.data.index.date).first()  # type: ignore

        for i in range(0, len(ax)):
            for grid in ["major", "minor"]:
                ax[i].grid(which=grid, color="gray", linestyle="--", linewidth=0.8, alpha=0.7)

            for spine in ax[i].spines.values():
                spine.set_edgecolor("black")
                spine.set_linestyle("-")
                spine.set_linewidth(1)
                spine.set_alpha(1)

            for start in start_of_day_indices:
                int_index = self.data.index.get_loc(start)
                ax[i].axvline(x=int_index, color="green", linestyle="--", linewidth=1)

            ax[i].xaxis.set_major_locator(MultipleLocator(30))

        mpf.show()
