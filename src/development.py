import json
import os
import warnings
from datetime import datetime, timedelta
from typing import List, Tuple

from backtest import backtest
from data.settings import OMX30_YAHOO
from services.storage import Storage
from services.ta.strategies.models import ComposeStrategiesListMethod
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)


set_handlers("development")
log = get_logger()


def run_full_strategies_generation(indicators_selector: List[Tuple[str, str]]):
    resolution = "2m"
    period_days = 60

    data = Storage(OMX30_YAHOO, resolution=resolution).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    log.warning("Generating strategies")
    backtest(
        data,
        indicators_selector,
        ComposeStrategiesListMethod.GENERATE,
        old_strategies_file_name=None,
        new_strategies_file_name="strategies_dev_3_indicators.json",
        indicators_filter=[],
        plot=False,
    )

    for i in range(3, 7):
        log.warning(f"Extending strategies ({i} -> {i + 1})")
        backtest(
            data,
            indicators_selector,
            ComposeStrategiesListMethod.EXTEND,
            old_strategies_file_name=f"strategies_dev_{i}_indicators.json",
            new_strategies_file_name=f"strategies_dev_{i + 1}_indicators.json",
            indicators_filter=[],
            plot=False,
        )

    resolution = "2m"
    period_days = 20

    data = Storage(OMX30_YAHOO, resolution=resolution).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    log.warning("Backtesting strategies")
    backtest(
        data,
        indicators_selector,
        ComposeStrategiesListMethod.READ,
        old_strategies_file_name="strategies_dev_7_indicators.json",
        new_strategies_file_name="strategies.json",
        indicators_filter=[],
        plot=False,
    )


def run_plotting_for_active_strategies(indicators_selector: List[Tuple[str, str]]):
    resolution = "2m"
    period_days = 5

    data = Storage(OMX30_YAHOO, resolution=resolution).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    backtest(
        data.copy(),
        indicators_selector,
        ComposeStrategiesListMethod.READ,
        old_strategies_file_name="strategies.json",
        new_strategies_file_name=None,
        indicators_filter=[],
        plot=True,
    )


def run_test_for_selected_indicators(indicators_selector: List[Tuple[str, str]]):
    resolution = "2m"
    period_days = 60

    data = Storage(OMX30_YAHOO, resolution=resolution).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    indicator_to_test = "PVT"
    new_strategies_file_name_prefix = f"strategies_dev_6_indicators_{indicator_to_test}_"

    # drift=2, length_ema=14
    for drift, length_ema in (
        [(i, 25) for i in range(4, 20, 2)] + [(i, 30) for i in range(4, 20, 2)] + [(i, 35) for i in range(4, 20, 2)]
    ):
        kwargs = {"drift": drift, "length_ema": length_ema}

        log.warning(f"Testing for {indicator_to_test}_{kwargs.items()}")
        backtest(
            data.copy(),
            indicators_selector,
            ComposeStrategiesListMethod.EXTEND,
            old_strategies_file_name="strategies_dev_5_indicators.json",
            new_strategies_file_name=new_strategies_file_name_prefix
            + f"{'_'.join([f'{k}={v}' for k, v in kwargs.items()])}.json",
            indicators_filter=[indicator_to_test],
            plot=False,
            **kwargs,
        )

    stats = []
    for file in os.listdir("src/data"):
        if file.startswith(new_strategies_file_name_prefix):
            strategies = json.load(open(f"src/data/{file}"))
            s = strategies[0]
            stats.append(
                (
                    file.replace(new_strategies_file_name_prefix, "").replace(".json", ""),
                    round(s["profitable_trades_share"] * s["total_profit"], 2),
                    s["profitable_trades_share"],
                    s["total_profit"],
                    s["name"],
                ),
            )

    log.warning(f"Stats for {indicator_to_test}")
    for s in sorted(stats, key=lambda x: x[1], reverse=True):
        log.info(">" + " | ".join(s))


if __name__ == "__main__":
    indicators_selector = [
        ("Trend", "ADX"),  # buy / sell
        ("Trend", "TII"),  # buy / sell
        ("Trend", "PSAR"),  # buy / sell
        ("Trend", "CHOP"),  # exit
        ("Overlap", "LINREG"),  # buy / sell
        ("Overlap", "GHLA"),  # buy / sell
        ("Overlap", "SUPERTREND"),  # buy / sell
        ("Momentum", "MACD_DEMA"),  # buy / sell
        ("Momentum", "STC"),  # buy / sell
        ("Momentum", "CCI"),  # buy / sell
        ("Momentum", "RVGI"),  # buy / sell
        ("Momentum", "STOCH"),  # buy / sell
        ("Cycles", "EBSW"),  # buy / sell
        ("Volatility", "STARC"),  # buy / sell
        ("Volatility", "MASSI"),  # buy / sell
        ("Volatility", "BBANDS"),  # buy / sell
        ("Volatility", "ACCBANDS"),  # buy / sell
        ("Volume", "PVT"),  # buy / sell
        ("Volume", "ADOSC"),  # buy / sell
        ("Volume", "CMF"),  # buy / sell
        ("Volume", "KVO"),  # buy / sell
    ]

    # run_full_strategies_generation(indicators_selector)
    # run_test_for_selected_indicators(indicators_selector)
    run_plotting_for_active_strategies(indicators_selector)
