import json
import os
import warnings
from datetime import datetime, timedelta
from enum import Enum
from itertools import product
from pprint import pprint

import pandas as pd
from pydantic import BaseModel

from config import SETTINGS
from services.storage.candle_quality import require_clean_bars
from services.storage.operators import Storage
from services.storage.windows import DataWindow
from services.ta.strategies.models.strategy import ComposeStrategiesListMethod
from tasks.backtest.runner import backtest_trade_strategies
from tasks.backtest.walk_forward import SelectionWalkForward, WalkForwardGrid
from utils.constants import TODAY_MIDNIGHT
from utils.logger.operators import get_logger, set_handlers

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


def _get_data(point_of_origin: datetime, period_days: int) -> pd.DataFrame:
    """Bars of the window, partial-candle days dropped (experiments never stop on data quality)."""
    window = DataWindow.days_before(point_of_origin, period_days)
    log.info(f"Get data: {window}")

    return require_clean_bars(window.slice(Storage().read()), min_clean_share=0.0)


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
            strategies_file_name_suffix_new=f"dev_{SETTINGS.STRATEGY.INDICATORS_START}" + (comment if comment else ""),
        )

        for i in range(SETTINGS.STRATEGY.INDICATORS_START, SETTINGS.STRATEGY.INDICATORS):
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
            f"Testing for {test_params.indicator_category}_{test_params.indicator_name}_{list(kwargs.items())}",
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


def run_selection_walk_forward(period_days: int, indicators_count: int, grid: WalkForwardGrid | None = None):
    """Compare daily-selection settings (SCORE_HALF_LIFE_DAYS, SCORE_PRIOR_TRADES, MIN_EDGE) on history."""
    data = _get_data(point_of_origin=TODAY_MIDNIGHT, period_days=period_days)
    log.warning(f"Walk-forward: simulating every {indicators_count}-indicator strategy over {period_days} days")

    walk_forward = SelectionWalkForward.from_indicator_combinations(data, indicators_count, grid or WalkForwardGrid())
    results = pd.DataFrame([result.model_dump() for result in walk_forward.run()])

    log.warning(
        f"Walk-forward over {len(walk_forward.evaluated_days)} days; "
        f"average candidate {round(100 * walk_forward.average_candidate_daily_return, 3)}%/day",
    )
    log.info("\n" + results.sort_values("total_return", ascending=False).to_string(index=False))


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
    get_statistics_per_indicator()

    is_strategies_generation = True
    is_full = True

    if is_strategies_generation:
        run_strategies_generation(period_days_back_test=90, period_days_forward_test=30, full=is_full)

    else:
        moving_average_types = [ma_type.value for ma_type in MovingAverageType]

        run_test_for_selected_indicators(
            period_days=90,
            test_params=TestParams(
                indicator_category="Trend",
                indicator_name="CHOP",
                indicators_count_base=6,
                kwargs_base={
                    "length": [i for i in range(5, 7, 1)],
                    "length_atr": [i for i in range(5, 7, 1)],
                    "scalar": [float(i) for i in range(45, 55, 2)],
                },
            ),
        )

    # # run_plotting_for_active_strategies(period_days=50)
    # # run_selection_walk_forward(period_days=540, indicators_count=3)
