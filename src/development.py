import json
import os
import warnings
from datetime import datetime, timedelta

import pandas as pd

from backtest import backtest
from config import SETTINGS_TRADE_NASDAQ, SETTINGS_TRADE_OMX
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

    period_days = 20

    data = Storage(settings).read()
    data = data.loc[
        (data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days))
        & (data.index < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
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

    indicator_to_test = ("Momentum", "STC")
    new_strategies_file_name_prefix = f"strategies_dev_6_{'-'.join(indicator_to_test)}_"

    for tclength, fast, slow in [(14, 22, i) for i in range(35, 55, 2)]:
        kwargs = {"tclength": tclength, "fast": fast, "slow": slow, "factor": 0.55}
        settings.INDICATORS[indicator_to_test[0]][indicator_to_test[1]] = kwargs

        log.warning(f"Testing for {indicator_to_test}_{list(kwargs.items())}")
        backtest(
            data.copy(),
            ComposeStrategiesListMethod.EXTEND,
            settings,
            old_strategies_file_name="strategies_dev_5.json",
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
        if not strategies:
            continue

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


def test_gaps(settings):
    from pprint import pprint

    period_days = 70

    close = "09:36"
    side = "BEAR"

    data = Storage(settings).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]
    data.index = pd.to_datetime(data.index)
    daily_data = data.resample("D")
    price_morning_high = daily_data["High"].apply(lambda x: x[x.index.time < pd.to_datetime(close).time()].max())
    price_morning_low = daily_data["Low"].apply(lambda x: x[x.index.time < pd.to_datetime(close).time()].min())
    price_morning_end = daily_data["Close"].apply(lambda x: x.at_time(close))
    price_day_close = daily_data["Close"].apply(lambda x: x.at_time("17:00"))
    result = pd.DataFrame(
        {
            f"Top price before {close}": price_morning_high,
            f"Low price before {close}": price_morning_low,
            f"End price at {close}": price_morning_end,
            "Price at 17:00": price_day_close,
        },
    )
    result.index = pd.to_datetime(result.index)
    grouped = result.groupby(result.index.date)
    result = grouped.agg(
        {
            f"Top price before {close}": "first",
            f"Low price before {close}": "first",
            f"End price at {close}": "first",
            "Price at 17:00": "last",
        },
    ).dropna()

    print(result)

    gaps = {}
    previous_day = None
    for index, row in result.iterrows():
        if previous_day is not None:
            gaps[previous_day] = {
                "high": row[f"Top price before {close}"] - result.loc[previous_day]["Price at 17:00"],
                "low": row[f"Low price before {close}"] - result.loc[previous_day]["Price at 17:00"],
                "close": row[f"End price at {close}"] - result.loc[previous_day]["Price at 17:00"],
            }

        previous_day = index

    pprint(gaps)

    for cut_off in range(5, 100, 2):
        counter = 0
        total = 0
        for gap in gaps.values():
            if (gap["high"] if side == "BULL" else (gap["low"] * -1)) > cut_off:
                total += cut_off
                counter += 1
            else:
                profit = gap["close"] * (1 if side == "BULL" else -1)
                total += profit
                if profit > 0:
                    counter += 1

        print(cut_off, round(counter / len(gaps), 2), round(total, 2))


if __name__ == "__main__":
    settings = SETTINGS_TRADE_NASDAQ
    settings = SETTINGS_TRADE_OMX

    # run_full_strategies_generation(settings)
    # run_test_for_selected_indicators(settings)
    # run_plotting_for_active_strategies(settings)

    test_gaps(settings)
