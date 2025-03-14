import json
import os
import warnings
from dataclasses import dataclass
from datetime import timedelta
from pprint import pprint

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


@dataclass
class TestedKwargs:
    indicator_to_test: tuple[str, str]
    kwargs: list[dict]

    @property
    def strategies_file_name_suffix_new_suffix(self) -> str:
        return f"dev_6_{'-'.join(self.indicator_to_test)}_"


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


def _generate_tested_kwargs() -> TestedKwargs:
    tested_kwargs = TestedKwargs(indicator_to_test=("Trend", "CHOP"), kwargs=[])

    # ma_list = [
    #     "sma",
    #     "ema",
    #     "dema",
    #     "fwma",
    #     # "hma",
    #     "linreg",
    #     "midpoint",
    #     "pwma",
    #     "rma",
    #     "sinwma",
    #     "swma",
    #     "t3",
    #     "tema",
    #     "trima",
    #     "vidya",
    #     "wma",
    #     "zlma",
    # ]
    # for ma in ma_list:
    for length_1 in range(40, 46, 2):
        for length_2 in range(16, 20, 2):
            # for length_3 in range(70, 90, 5):
            #     # for threshold in range(57, 61, 2):
            #     if length_1 >= length_2:
            #         continue

            kwargs = {"length": length_1, "bars": length_2}

            # -----------
            already_tested = False
            for file in sorted(os.listdir("src/config")):
                if (
                    tested_kwargs.strategies_file_name_suffix_new_suffix
                    + f"{'_'.join([f'{k}={v}' for k, v in kwargs.items()])}"
                    in file
                ):
                    already_tested = True

            if already_tested:
                continue

            tested_kwargs.kwargs.append(kwargs)

    return tested_kwargs


def run_test_for_selected_indicators(settings, period_days: int):
    tested_kwargs = _generate_tested_kwargs()

    for kwargs in tested_kwargs.kwargs:
        settings.INDICATORS[tested_kwargs.indicator_to_test[0]][tested_kwargs.indicator_to_test[1]] = kwargs

        log.warning(f"Testing for {tested_kwargs.indicator_to_test}_{list(kwargs.items())}")
        backtest_trade_strategies(
            _get_data(period_days, settings),
            ComposeStrategiesListMethod.EXTEND,
            settings,
            strategies_file_name_suffix_old="dev_5",
            strategies_file_name_suffix_new=tested_kwargs.strategies_file_name_suffix_new_suffix
            + f"{'_'.join([f'{k}={v}' for k, v in kwargs.items()])}",
            indicators_filter=[tested_kwargs.indicator_to_test[1]],
            **kwargs,
        )

    stats = []
    for file in os.listdir("src/config"):
        if tested_kwargs.strategies_file_name_suffix_new_suffix not in file:
            continue

        strategies = json.load(open(f"src/config/{file}"))
        if not strategies:
            continue

        s = strategies[0]

        stats.append(
            (
                file.replace(tested_kwargs.strategies_file_name_suffix_new_suffix, "").replace(".json", ""),
                round(s["profitable_trades_share"] * s["total_profit"], 2),
                s["profitable_trades_share"],
                s["total_profit"],
                s["name"],
                round(sum([i["profitable_trades_share"] for i in strategies]), 2),
            ),
        )

    log.warning(f"Stats for {tested_kwargs.indicator_to_test}")
    for s in sorted(stats, key=lambda x: x[5], reverse=True):
        log.info("> {}".format(" | ".join([str(i) for i in s])))


def get_statistics_per_indicator():
    for file in sorted(os.listdir("src/config")):
        if "OMX_trade_strategies" not in file:
            continue

        print(f"\n\n\n{file}\n----------------------\n")
        with open(f"src/config/{file}") as f:
            strategies = json.load(f)

            indicators = {}
            for strategy in strategies:
                for strategy_indicator in [i.strip() for i in strategy["name"].split("|")]:
                    indicators.setdefault(strategy_indicator, {"counter": 0, "sum_eff": 0})
                    indicators[strategy_indicator]["counter"] += 1
                    indicators[strategy_indicator]["sum_eff"] += strategy["profitable_trades_share"]

            print("Total:", sum([i["profitable_trades_share"] for i in strategies]), "\n")

        pprint(
            sorted(
                [
                    (k, (v["counter"], round(v["sum_eff"], 2), round(v["sum_eff"] / v["counter"], 2)))
                    for k, v in indicators.items()
                ],
                key=lambda x: x[1][2],
                reverse=True,
            ),
        )


if __name__ == "__main__":
    settings = SETTINGS_TRADE_STRATEGIES_OMX
    run_strategies_generation(settings, period_days=40, full=True)
    # run_test_for_selected_indicators(settings, period_days=60)
    # run_plotting_for_active_strategies(settings, period_days=5)
    get_statistics_per_indicator()
