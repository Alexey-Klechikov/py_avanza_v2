import json
import os
import warnings
from datetime import timedelta

import pandas as pd

from config import SETTINGS_TRADE_STRATEGIES_OMX
from services import Storage
from services.ta.strategies.models import ComposeStrategiesListMethod
from tasks.trade_strategies import backtest_trade_strategies
from utils.constants import TODAY_MIDNIGHT
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.set_option("display.max_rows", None)


set_handlers("development")
log = get_logger()


def _get_data(period_days: int, settings, resolution: str | None = None):
    data = Storage(settings, resolution).read()
    data = data.loc[(data.index >= TODAY_MIDNIGHT - timedelta(days=period_days)) & (data.index < TODAY_MIDNIGHT)]
    data.index = pd.to_datetime(data.index)

    return data


def run_strategies_generation(settings, period_days: int, full: bool, comment: str | None = None):
    if full:
        log.warning("Generating strategies")
        backtest_trade_strategies(
            _get_data(period_days + 20, settings),
            ComposeStrategiesListMethod.GENERATE,
            settings,
            strategies_file_name_suffix_new="dev_3",
        )

        for i in range(3, settings.TRADING_STRATEGY_INDICATORS):
            log.warning(f"Extending strategies ({i} -> {i + 1})")
            backtest_trade_strategies(
                _get_data(period_days + 20, settings),
                ComposeStrategiesListMethod.EXTEND,
                settings,
                strategies_file_name_suffix_old=f"dev_{i}",
                strategies_file_name_suffix_new=f"dev_{i + 1}",
            )

    log.warning("Backtesting strategies")
    backtest_trade_strategies(
        _get_data(period_days, settings),
        ComposeStrategiesListMethod.READ,
        settings,
        strategies_file_name_suffix_old=f"dev_{settings.TRADING_STRATEGY_INDICATORS}",
        strategies_file_name_suffix_new=comment,
    )


def run_plotting_for_active_strategies(settings, period_days: int):
    backtest_trade_strategies(
        _get_data(period_days, settings),
        ComposeStrategiesListMethod.READ,
        settings,
        plot=True,
    )


def run_test_for_selected_indicators(settings, period_days: int):
    indicator_to_test = ("Volume", "KVO")
    strategies_file_name_suffix_new_suffix = f"dev_6_{'-'.join(indicator_to_test)}_"

    ma_list = [
        "sma",
        "ema",
        "dema",
        "fwma",
        # "hma",
        "linreg",
        "midpoint",
        "pwma",
        "rma",
        "sinwma",
        "swma",
        "t3",
        "tema",
        "trima",
        "vidya",
        "wma",
        "zlma",
    ]
    for ma in ma_list:
        for length in [i for i in range(7, 12, 1)]:
            kwargs = {"fast": 14, "slow": 30, "signal": 14, "mamode": ma, "length_divergence": 28}
            settings.INDICATORS[indicator_to_test[0]][indicator_to_test[1]] = kwargs

            log.warning(f"Testing for {indicator_to_test}_{list(kwargs.items())}")
            backtest_trade_strategies(
                _get_data(period_days, settings),
                ComposeStrategiesListMethod.EXTEND,
                settings,
                strategies_file_name_suffix_old="dev_5",
                strategies_file_name_suffix_new=strategies_file_name_suffix_new_suffix
                + f"{'_'.join([f'{k}={v}' for k, v in kwargs.items()])}",
                indicators_filter=[indicator_to_test[1]],
                **kwargs,
            )

    stats = []
    for file in os.listdir("src/config"):
        if strategies_file_name_suffix_new_suffix not in file:
            continue

        strategies = json.load(open(f"src/config/{file}"))
        if not strategies:
            continue

        s = strategies[0]

        stats.append(
            (
                file.replace(strategies_file_name_suffix_new_suffix, "").replace(".json", ""),
                round(s["profitable_trades_share"] * s["total_profit"], 2),
                s["profitable_trades_share"],
                s["total_profit"],
                s["name"],
                round(sum([i["profitable_trades_share"] for i in strategies]), 2),
            ),
        )

    log.warning(f"Stats for {indicator_to_test}")
    for s in sorted(stats, key=lambda x: x[1], reverse=True):
        log.info("> " + " | ".join([str(i) for i in s]))


if __name__ == "__main__":
    settings = SETTINGS_TRADE_STRATEGIES_OMX
    run_strategies_generation(settings, period_days=40, full=True)
    # run_test_for_selected_indicators(settings, period_days=60)
    # run_plotting_for_active_strategies(settings, period_days=5)
