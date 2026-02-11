import json
import os
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta
from pprint import pprint

import pandas as pd

from config import SETTINGS
from services.storage.operators import Storage
from services.ta.strategies.models.strategy import ComposeStrategiesListMethod
from tasks.trade_strategies.backtest import backtest_trade_strategies
from utils.constants import TODAY_MIDNIGHT
from utils.logger.operators import get_logger, set_handlers

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


def _get_data(point_of_origin: datetime, period_days: int):
    log.info(f"Get data: {(point_of_origin - timedelta(days=period_days)).date()} - {point_of_origin.date()}")

    data = Storage().read()
    data = data.loc[(data.index >= point_of_origin - timedelta(days=period_days)) & (data.index < point_of_origin)]
    data.index = pd.to_datetime(data.index)

    return data


def run_strategies_generation(
    period_days_back_test: int,
    period_days_forward_test: int,
    full: bool,
    comment: str | None = None,
):
    if full:
        log.warning(f"Back-test strategies for {SETTINGS.NAME} ({SETTINGS.RESOLUTION}, {period_days_back_test} days)")
        backtest_trade_strategies(
            _get_data(
                point_of_origin=(TODAY_MIDNIGHT - timedelta(days=period_days_forward_test)),
                period_days=period_days_back_test,
            ),
            ComposeStrategiesListMethod.GENERATE,
            strategies_file_name_suffix_new="dev_3" + (comment if comment else ""),
        )

        for i in range(3, SETTINGS.STRATEGY.INDICATORS):
            log.warning(
                "Back-test strategies ({} -> {}) for {} ({}, {} days)".format(
                    i,
                    i + 1,
                    SETTINGS.NAME,
                    SETTINGS.RESOLUTION,
                    period_days_back_test,
                ),
            )
            backtest_trade_strategies(
                _get_data(
                    point_of_origin=(TODAY_MIDNIGHT - timedelta(days=period_days_forward_test)),
                    period_days=period_days_back_test,
                ),
                ComposeStrategiesListMethod.EXTEND,
                strategies_file_name_suffix_old=f"dev_{i}" + (comment if comment else ""),
                strategies_file_name_suffix_new=f"dev_{i + 1}" + (comment if comment else ""),
            )

    log.warning(
        f"Forward-test strategies for {SETTINGS.NAME} ({SETTINGS.RESOLUTION}, {period_days_forward_test} days)",
    )
    backtest_trade_strategies(
        _get_data(point_of_origin=TODAY_MIDNIGHT, period_days=period_days_forward_test),
        ComposeStrategiesListMethod.READ,
        strategies_file_name_suffix_old=f"dev_{SETTINGS.STRATEGY.INDICATORS}" + (comment if comment else ""),
        strategies_file_name_suffix_new=comment,
    )


def run_plotting_for_active_strategies(period_days: int):
    backtest_trade_strategies(
        _get_data(point_of_origin=TODAY_MIDNIGHT, period_days=period_days),
        ComposeStrategiesListMethod.READ,
        plot=True,
    )


def _generate_tested_kwargs() -> TestedKwargs:
    tested_kwargs = TestedKwargs(indicator_to_test=("Volume", "PVT"), kwargs=[])

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
    for length_1 in range(8, 20, 2):
        for length_2 in range(16, 28, 2):
            #     for length_3 in range(10, 18, 2):
            #         #     # for threshold in range(57, 61, 2):
            #         if length_1 > length_2:
            #             continue

            kwargs = {"drift": length_1, "length_sma": length_2, "length_divergence": 24}

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


def run_test_for_selected_indicators(period_days: int):
    tested_kwargs = _generate_tested_kwargs()

    for kwargs in tested_kwargs.kwargs:
        SETTINGS.INDICATORS[tested_kwargs.indicator_to_test[0]][tested_kwargs.indicator_to_test[1]] = kwargs

        log.warning(f"Testing for {tested_kwargs.indicator_to_test}_{list(kwargs.items())}")
        backtest_trade_strategies(
            _get_data(point_of_origin=TODAY_MIDNIGHT, period_days=period_days),
            ComposeStrategiesListMethod.EXTEND,
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
                # s["name"],
                "GLOBAL_STATS",
                round(sum([i["profitable_trades_share"] for i in strategies]), 2),
                round(sum([round(i["profitable_trades_share"] * i["total_profit"], 2) for i in strategies]), 2),
            ),
        )

    log.warning(f"Stats for {tested_kwargs.indicator_to_test}")
    log.info(
        " | ".join(
            [
                "normalized_profit [top]",
                "profitable_trades_share [top]",
                "total_profit [top]",
                "profitable_trades_share [sum all]",
                "normalized_profit [sum all]",
            ],
        ),
    )
    for s in sorted(stats, key=lambda x: x[6], reverse=True):
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
    # run_strategies_generation(period_days_back_test=90, period_days_forward_test=30, full=True)

    run_test_for_selected_indicators(period_days=90)
    # run_plotting_for_active_strategies(period_days=50)
    # get_statistics_per_indicator()
