"""
This code is forked from
https://medium.com/automation-generation/algorithmically-detecting-and-trading-technical-chart-patterns-with-python-c577b3a396ed

[WIP - TODO: need work]

"""

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema


class CustomCandlestickPatterns:
    def __init__(self, data: pd.DataFrame, smoothing: int, max_window_time_min: int):
        self.data = data
        self.smoothing = smoothing
        self.max_window_time_min = max_window_time_min

        self._peaks: pd.DataFrame = pd.DataFrame()

    def calculate_peaks(self):
        data_smooth = self.data["Close"].rolling(window=self.smoothing).mean()

        price_local_max_index = []
        for i in argrelextrema(data_smooth.values, np.greater)[0]:
            if i < self.smoothing:
                continue
            price_local_max_index.append(self.data.iloc[i - self.smoothing : i + 1]["Close"].idxmax())

        price_local_min_index = []
        for i in argrelextrema(data_smooth.values, np.less)[0]:
            if i < self.smoothing:
                continue
            price_local_min_index.append(self.data.iloc[i - self.smoothing : i + 1]["Close"].idxmin())

        maxima = pd.DataFrame(self.data.loc[price_local_max_index])
        minima = pd.DataFrame(self.data.loc[price_local_min_index])

        peaks = pd.concat([maxima, minima]).sort_index()["Close"]
        peaks = peaks[~peaks.index.duplicated(keep="first")]

        self._peaks = pd.DataFrame(peaks)

    def _append_signal(self, column_name: str, window_end_index: pd.Timestamp, signal: int):
        try:
            signal_index = window_end_index
            self.data.loc[signal_index, column_name] = signal

        except KeyError:
            pass

    def append_head_and_shoulders(self, necklines_diff: float = 0.02):
        column_name = "PTNHEADANDSHOULDERS"

        self.data[column_name] = 0
        for i in range(5, len(self._peaks)):
            window = self._peaks.iloc[i - 5 : i]

            if ((window.index[-1] - window.index[0]).seconds // 60) > self.max_window_time_min:
                continue

            a, b, c, d, e = (float(i) for i in window.iloc[0:5]["Close"])

            # Inverse Head and Shoulders
            #    b        d
            #    /\      /\            /
            #   /  \    /  \          /
            #  /    \  /    \   ->   /
            # a      \/      e
            #         c

            if all(
                [
                    a < b,
                    c < min(a, b, d, e),
                    e < d,
                    abs(b - d) <= np.mean([b, d]) * necklines_diff,
                ],
            ):
                for i, row in self.data.loc[window.index[-1] :].iterrows():
                    if row["Close"] > d:
                        self._append_signal(column_name, i, 100)  # type: ignore
                        break

            # Head and Shoulders
            #         c
            # a      /\      e
            #  \    /  \    /      \
            #   \  /    \  /   ->   \
            #    \/      \/          \
            #     b       d

            if all(
                [
                    a > b,
                    c > max(a, b, d, e),
                    e > d,
                    abs(b - d) <= np.mean([b, d]) * necklines_diff,
                ],
            ):
                for i, row in self.data.loc[window.index[-1] :].iterrows():
                    if row["Close"] < d:
                        self._append_signal(column_name, i, -100)  # type: ignore
                        break

    def append_double_top_bottom(self, peaks_diff: float = 0.03):
        column_name = "PTNDOUBLETOPBOTTOM"

        self.data[column_name] = 0
        for i in range(5, len(self._peaks)):
            window = self._peaks.iloc[i - 5 : i]

            if ((window.index[-1] - window.index[0]).seconds // 60) > self.max_window_time_min:
                continue

            a, b, c, d, e = (float(i) for i in window.iloc[0:5]["Close"])

            # Double tops
            #     b      d
            #     /\    /\
            #    /  \  /  \          /
            #   /    \/    \   ->   /
            #  /     c      \      /
            # a              e

            if all(
                [
                    a < min(b, c, d),
                    c < min(b, d),
                    e < min(b, c, d),
                    abs(b - d) <= np.mean([b, d]) * peaks_diff,
                ],
            ):
                self._append_signal(column_name, window.index[-1], 100)

            # Double bottoms
            # a             e
            # \     c      /
            #  \    /\    /      \
            #   \  /  \  /   ->   \
            #    \/    \/          \
            #    b      d

            if all(
                [
                    a > max(b, c, d),
                    c > max(b, d),
                    e > max(b, c, d),
                    abs(b - d) <= np.mean([b, d]) * peaks_diff,
                ],
            ):
                self._append_signal(column_name, window.index[-1], -100)

    def append_triangle(self, peaks_diff: float = 0.03):
        column_name = "PTNTRIANGLE"

        self.data[column_name] = 0
        for i in range(6, len(self._peaks)):
            window = self._peaks.iloc[i - 6 : i]

            if ((window.index[-1] - window.index[0]).seconds // 60) > self.max_window_time_min:
                continue

            a, b, c, d, e, f = (float(i) for i in window.iloc[0:6]["Close"])

            # Double tops
            #                 f
            #     b      d   /
            #     /\    /\  /
            #    /  \  /  \/          /
            #   /    \/    e   ->    /
            #  /     c              /
            # a

            if all(
                [
                    a < min(b, c, d, e, f),
                    a < c < e,
                    f > max(a, b, c, d, e),
                    abs(b - d) <= np.mean([b, d]) * peaks_diff,
                ],
            ):
                self._append_signal(column_name, window.index[-1], 100)

            # Double bottoms
            # a
            # \     c
            #  \    /\    e        \
            #   \  /  \  /\   ->    \
            #    \/    \/  \         \
            #    b      d   \
            #                f

            if all(
                [
                    a > max(b, c, d, e, f),
                    e < c < a,
                    f < min(a, b, c, d, e),
                    abs(b - d) <= np.mean([b, d]) * peaks_diff,
                ],
            ):
                self._append_signal(column_name, window.index[-1], -100)

    def append_pennants(self):
        column_name = "PTNPENNANTS"

        self.data[column_name] = 0
        for i in range(6, len(self._peaks)):
            window = self._peaks.iloc[i - 6 : i]

            if ((window.index[-1] - window.index[0]).seconds // 60) > self.max_window_time_min:
                continue

            a, b, c, d, e, f = (float(i) for i in window.iloc[0:6]["Close"])

            # Double tops
            #               f
            #     b        /
            #     /\    d /
            #    /  \  /\/          /
            #   /    \/  e   ->    /
            #  /     c            /
            # a

            if all(
                [
                    a < min(b, c, d, e, f),
                    f > b > max(a, c, d, e),
                    a < c < min(b, d, e, f),
                    max(a, c, e) < d < min(b, f),
                    max(a, c) < e < min(b, d, f),
                    f > max(a, b, c, d, e),
                ],
            ):
                self._append_signal(column_name, window.index[-1], -100)

            # Double bottoms
            # a
            # \     c
            #  \    /\  e        \
            #   \  /  \/\   ->    \
            #    \/   d  \         \
            #    b        \
            #              f

            if all(
                [
                    a > max(b, c, d, e, f),
                    f < b < min(a, c, d, e),
                    a > c > max(b, d, e, f),
                    min(a, c, e) > d > max(b, f),
                    min(a, c) > e > max(b, d, f),
                    f < min(a, b, c, d, e),
                ],
            ):
                self._append_signal(column_name, window.index[-1], 100)
