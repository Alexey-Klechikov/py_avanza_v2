import warnings
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel

from data.settings import OMX30_YAHOO
from services.storage import Storage
from services.ta.figure import Figure
from services.ta.indicators.models import Indicator, Panel, Plot, Plots
from services.ta.operators import get_indicators
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)


set_handlers("development")
log = get_logger()

data = pd.DataFrame()


class Order(BaseModel):
    buy_price: float
    buy_datetime: Any
    sell_price: Optional[float] = None
    sell_datetime: Optional[Any] = None

    def sell(self, sell_price: float, sell_datetime: Any, instrument_type: str):
        self.sell_price = sell_price
        self.sell_datetime = sell_datetime

        profit = self.sell_price - self.buy_price
        profit = profit if instrument_type == "BULL" else -profit

        trading_time = (self.sell_datetime - self.buy_datetime).seconds / 60

        log.info(
            f"{self.buy_datetime.date()} {instrument_type}: "
            f"{self.buy_price} -> {self.sell_price} "
            f"at {self.buy_datetime.time()} -> {self.sell_datetime.time()}: "
            f"{round(profit, 2)} in {trading_time} min"
            f" ({('+' if profit > 0 else '-') * (1 + int(round(abs(profit)) // 3))})",
        )


class Wallet(BaseModel):
    BULL: Optional[Order] = None
    BEAR: Optional[Order] = None


def _get_active_indicators(
    all_indicators: Dict[str, Dict[str, Indicator]],
    active_indicators_selector: List[Tuple[str, str]],
) -> List[Indicator]:
    active_indicators: List[Indicator] = []
    for category, name in active_indicators_selector:
        indicator = all_indicators.get(category, {}).get(name)
        if not indicator:
            log.warning(f"Indicator {name} from category {category} does not exist.")
            continue

        if indicator.plots is None:
            log.warning(f"Indicator {name}-{category} does not have any plots.")
            continue

        active_indicators.append(indicator)

    return active_indicators


def _consider_signals(active_indicators: List[Indicator]):
    for column in ["LONG", "SHORT", "EXIT", "STOP_LOSS_LONG", "STOP_LOSS_SHORT"]:
        combination_condition = all if column in ["LONG", "SHORT"] else any

        signal_methods = [
            indicator.signal.__getattribute__(column)
            for indicator in active_indicators
            if indicator.signal.__getattribute__(column) is not None
        ]

        for i, row in data.iterrows():
            data.at[i, column] = (
                np.nan
                if not signal_methods or not combination_condition(signal_method(row) for signal_method in signal_methods)
                else row[column]
            )

    for column in ["LONG", "SHORT", "EXIT"]:
        for non_trading_time in (["09:00", "10:00"], ["17:15", "17:30"]):
            data.loc[data.between_time(non_trading_time[0], non_trading_time[1]).index, column] = np.nan

        data.loc[data.between_time("17:15", "17:16").index, "EXIT"] = (data["High"] + data["Low"]) / 2


def _consider_trading_logic():
    wallet = Wallet()
    for i, row in data.iterrows():
        if (
            wallet.BULL is None
            and row["LONG"] > 0
            and np.isnan(row["STOP_LOSS_LONG"])
            and np.isnan(row["EXIT"])
            and np.isnan(row["SHORT"])
        ):
            wallet.BULL = Order(buy_price=row["LONG"], buy_datetime=i)

            if wallet.BEAR is not None:
                wallet.BEAR.sell(row["LONG"], i, "BEAR")
                wallet.BEAR = None

        elif wallet.BULL is not None and (row["STOP_LOSS_LONG"] > 0 or row["EXIT"] > 0):
            sell_price = row["STOP_LOSS_LONG"] if row["STOP_LOSS_LONG"] > 0 else row["EXIT"]
            wallet.BULL.sell(sell_price, i, "BULL")
            data.at[i, "EXIT"] = sell_price
            wallet.BULL = None

        if (
            wallet.BEAR is None
            and row["SHORT"] > 0
            and np.isnan(row["STOP_LOSS_SHORT"])
            and np.isnan(row["EXIT"])
            and np.isnan(row["LONG"])
        ):
            wallet.BEAR = Order(buy_price=row["SHORT"], buy_datetime=i)

            if wallet.BULL is not None:
                wallet.BULL.sell(row["SHORT"], i, "BULL")
                wallet.BULL = None

        elif wallet.BEAR is not None and (row["STOP_LOSS_SHORT"] > 0 or row["EXIT"] > 0):
            sell_price = row["STOP_LOSS_SHORT"] if row["STOP_LOSS_SHORT"] > 0 else row["EXIT"]
            wallet.BEAR.sell(sell_price, i, "BEAR")
            data.at[i, "EXIT"] = sell_price
            wallet.BEAR = None


def plot_indicators(
    active_indicators: List[Indicator],
    show_signals: bool = False,
):
    figure = Figure(data=data)
    for indicator in active_indicators:
        figure.add_plot(indicator.plots)

    if show_signals:
        data["LONG"] = data["High"]
        data["SHORT"] = data["Low"]
        data["EXIT"] = (data["High"] + data["Low"]) / 2
        data["STOP_LOSS_LONG"] = data["High"]
        data["STOP_LOSS_SHORT"] = data["Low"]

        _consider_signals(active_indicators)
        _consider_trading_logic()

        plot_signals = Plots(
            panel=Panel.MAIN,
            list=[
                Plot(columns=[column], type="scatter", color=color, markersize=50)
                for column, color in [("LONG", "green"), ("SHORT", "red"), ("EXIT", "black")]
                if not data[column].isnull().all()
            ],
        )

        figure.add_plot(plot_signals)

    figure.show()


if __name__ == "__main__":
    data = Storage(OMX30_YAHOO, resolution="5m").read()
    data = data.loc[data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=5)]

    indicators = get_indicators(data)
    active_indicators_selector = [
        ("Trend", "CKSP"),  # stop loss
        ("Trend", "ADX"),  # buy / sell
        ("Trend", "TII"),  # buy / sell
        # ("Trend", "PSAR"),
        # ("Trend", "CHOP"),
        # ("Trend", "CKSP"),
        # ("Overlap", "LINREG"),
        # ("Overlap", "GHLA"),
        # ("Momentum", "MACD_DEMA"),
        # ("Momentum", "STC"),
        # ("Momentum", "CCI"),
        # ("Momentum", "RVGI"),
        # ("Momentum", "STOCH"),
        # ("Cycles", "EBSW"),
        # ("Volatility", "STARC"),
        # ("Volatility", "MASSI"),
        # ("Volatility", "BBANDS"),
        # ("Volatility", "ACCBANDS"),
        # ("Volume", "PVT"),
        # ("Volume", "ADOSC"),
        # ("Volume", "CMF"),
        # ("Volume", "KVO"),
    ]

    log.info(
        f"Indicators: {' | '.join([(category + '-' + indicator) for category, indicator in active_indicators_selector])}",
    )

    plot_indicators(
        active_indicators=_get_active_indicators(indicators, active_indicators_selector),
        show_signals=True,
    )
