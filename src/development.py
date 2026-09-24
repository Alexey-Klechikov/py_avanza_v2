import json
import os
import warnings
from datetime import datetime, timedelta
from pprint import pprint
from itertools import product

import pandas as pd

from config import SETTINGS
from services.storage.operators import Storage
from services.ta.strategies.models.strategy import ComposeStrategiesListMethod
from tasks.backtest import backtest_trade_strategies
from utils.constants import TODAY_MIDNIGHT
from utils.logger.operators import get_logger, set_handlers
from enum import Enum
from pydantic import BaseModel

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.set_option("display.max_rows", None)


set_handlers("development")
log = get_logger()


class MovingAverageType(Enum):
    SMA = "sma"
    EMA = "ema"
    DEMA = "dema"
    FWMA = "fwma"
    LINREG = "linreg"
    MIDPOINT = "midpoint"
    PWMA = "pwma"
    RMA = "rma"
    SINWMA = "sinwma"
    SWMA = "swma"
    T3 = "t3"
    TEMA = "tema"
    TRIMA = "trima"
    VIDYA = "vidya"
    WMA = "wma"
    ZLMA = "zlma"


class TestParams(BaseModel):
    indicator_category: str
    indicator_name: str
    indicators_count_base: int
    kwargs_base: dict

    _kwargs: list[dict] = []

    @property
    def strategies_file_name_new_suffix(self) -> str:
        return f"dev_{self.indicators_count_base + 1}_{self.indicator_category}_{self.indicator_name}_"

    def _generate_kwargs(self) -> None:
        keys = list(self.kwargs_base)
        choices = [value if isinstance(value, list) else [value] for value in self.kwargs_base.values()]

        self._kwargs = [dict(zip(keys, reversed(combination))) for combination in product(*reversed(choices))]

    def _drop_tested_kwargs(self) -> None:
        untested_kwargs = []

        for kwarg in self._kwargs:
            already_tested = False
            for file in sorted(os.listdir("src/config")):
                if (
                    self.strategies_file_name_new_suffix + f"{'_'.join([f'{k}={v}' for k, v in kwarg.items()])}"
                    in file
                ):
                    already_tested = True
                    break

            if not already_tested:
                untested_kwargs.append(kwarg)

        self._kwargs = untested_kwargs

    def get_kwargs(self) -> list[dict]:
        self._generate_kwargs()
        self._drop_tested_kwargs()
        return self._kwargs


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


def run_test_for_selected_indicators(period_days: int, test_params: TestParams):
    for kwargs in test_params.get_kwargs():
        SETTINGS.INDICATORS[test_params.indicator_category][test_params.indicator_name] = kwargs

        log.warning(
            f"Testing for {test_params.indicator_category}_{test_params.indicator_name}_{list(kwargs.items())}"
        )
        backtest_trade_strategies(
            _get_data(point_of_origin=TODAY_MIDNIGHT, period_days=period_days),
            ComposeStrategiesListMethod.EXTEND,
            strategies_file_name_suffix_old=f"dev_{test_params.indicators_count_base}",
            strategies_file_name_suffix_new=test_params.strategies_file_name_new_suffix
            + f"{'_'.join([f'{k}={v}' for k, v in kwargs.items()])}",
            indicators_filter=[test_params.indicator_name],
            **kwargs,
        )

    stats = []
    for file in os.listdir("src/config"):
        if test_params.strategies_file_name_new_suffix not in file:
            continue

        strategies = json.load(open(f"src/config/{file}"))
        if not strategies:
            continue

        s = strategies[0]

        stats.append(
            (
                file.replace(test_params.strategies_file_name_new_suffix, "").replace(".json", ""),
                round(s["profitable_trades_share"] * s["total_profit"], 2),
                s["profitable_trades_share"],
                s["total_profit"],
                # s["name"],
                "GLOBAL_STATS",
                round(sum([i["profitable_trades_share"] for i in strategies]), 2),
                round(sum([round(i["profitable_trades_share"] * i["total_profit"], 2) for i in strategies]), 2),
            ),
        )

    log.warning(f"Stats for {test_params.indicator_category}_{test_params.indicator_name}")
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
    run_strategies_generation(period_days_back_test=90, period_days_forward_test=30, full=True)
    # run_plotting_for_active_strategies(period_days=50)
    get_statistics_per_indicator()

    raise SystemExit

    moving_average_types = [ma_type.value for ma_type in MovingAverageType]

    run_test_for_selected_indicators(
        period_days=90,
        test_params=TestParams(
            indicator_category="Volatility",
            indicator_name="ACCBANDS",
            indicators_count_base=6,
            kwargs_base={
                "length": list(range(8, 16, 2)),
                "c": list(range(1, 3)),
                "mamode": moving_average_types,
            },
        ),
    )
