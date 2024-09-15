import json
import os
import warnings
from datetime import datetime, timedelta

from backtest import backtest
from config.settings import SETTINGS
from services.storage import Storage
from services.ta.strategies.models import ComposeStrategiesListMethod
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)


set_handlers("development")
log = get_logger()


def run_full_strategies_generation(settings):
    period_days = 60

    data = Storage(settings).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    log.warning("Generating strategies")
    backtest(
        data,
        ComposeStrategiesListMethod.GENERATE,
        settings,
        old_strategies_file_name=None,
        new_strategies_file_name="strategies_dev_3.json",
        indicators_filter=[],
        plot=False,
    )

    for i in range(3, settings.TRADING_STRATEGY_INDICATORS):
        log.warning(f"Extending strategies ({i} -> {i + 1})")
        backtest(
            data,
            ComposeStrategiesListMethod.EXTEND,
            settings,
            old_strategies_file_name=f"strategies_dev_{i}.json",
            new_strategies_file_name=f"strategies_dev_{i + 1}.json",
            indicators_filter=[],
            plot=False,
        )

    period_days = 30

    data = Storage(settings).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    log.warning("Backtesting strategies")
    backtest(
        data,
        ComposeStrategiesListMethod.READ,
        settings,
        old_strategies_file_name=f"strategies_dev_{settings.TRADING_STRATEGY_INDICATORS}.json",
        new_strategies_file_name="strategies.json",
        indicators_filter=[],
        plot=False,
    )


def run_plotting_for_active_strategies(settings):
    period_days = 5

    data = Storage(settings).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    backtest(
        data.copy(),
        ComposeStrategiesListMethod.READ,
        settings,
        old_strategies_file_name="strategies.json",
        new_strategies_file_name=None,
        indicators_filter=[],
        plot=True,
    )


def run_test_for_selected_indicators(settings):
    period_days = 60

    data = Storage(settings).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    indicator_to_test = ("Overlap", "LINREG")
    new_strategies_file_name_prefix = f"strategies_dev_7_{'-'.join(indicator_to_test)}_"

    for length, c in [(i, 0.26) for i in range(6, 18, 2)]:
        kwargs = {"length": length, "limit": c}
        settings.INDICATORS[indicator_to_test[0]][indicator_to_test[1]] = kwargs

        log.warning(f"Testing for {indicator_to_test}_{kwargs.items()}")
        backtest(
            data.copy(),
            ComposeStrategiesListMethod.EXTEND,
            settings,
            old_strategies_file_name="strategies_dev_6.json",
            new_strategies_file_name=new_strategies_file_name_prefix
            + f"{'_'.join([f'{k}={v}' for k, v in kwargs.items()])}.json",
            indicators_filter=[indicator_to_test[1]],
            plot=False,
            **kwargs,
        )

    new_strategies_file_name_prefix = f"{settings.FILE_PREFIX}_{new_strategies_file_name_prefix}"

    stats = []
    for file in os.listdir("src/config"):
        if not file.startswith(new_strategies_file_name_prefix):
            continue

        strategies = json.load(open(f"src/config/{file}"))
        s = strategies[0]
        stats.append(
            (
                file.replace(new_strategies_file_name_prefix, "").replace(".json", ""),
                round(s["profitable_trades_share"] * s["total_profit"], 2),
                s["profitable_trades_share"],
                s["total_profit"],
                s["name"],
                round(sum([i["profitable_trades_share"] for i in strategies])),
            ),
        )

    log.warning(f"Stats for {indicator_to_test}")
    for s in sorted(stats, key=lambda x: x[1], reverse=True):
        log.info("> " + " | ".join([str(i) for i in s]))


if __name__ == "__main__":
    settings = SETTINGS.NASDAQ

    # run_full_strategies_generation(settings)
    # run_test_for_selected_indicators(settings)
    run_plotting_for_active_strategies(settings)
