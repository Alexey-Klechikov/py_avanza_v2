import json
import os
import warnings
from datetime import datetime, timedelta

import pandas as pd

from backtest import backtest
from config import SETTINGS_TRADE_OMX
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

    period_days = 60

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

    period_days = 90

    eod = "16:50"
    close = "10:00"
    side = "BULL"

    data = Storage(settings).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]
    data.index = pd.to_datetime(data.index)
    daily_data = data.resample("D")
    price_morning_high = daily_data["High"].apply(lambda x: x[x.index.time < pd.to_datetime(close).time()].max())
    price_morning_low = daily_data["Low"].apply(lambda x: x[x.index.time < pd.to_datetime(close).time()].min())
    price_morning_end = daily_data["Close"].apply(lambda x: x.at_time(close))
    price_day_close = daily_data["Close"].apply(lambda x: x.at_time(eod))
    result = pd.DataFrame(
        {
            f"Top price before {close}": price_morning_high,
            f"Low price before {close}": price_morning_low,
            f"End price at {close}": price_morning_end,
            "Price at eod": price_day_close,
        },
    )

    result.index = pd.to_datetime(result.index)
    grouped = result.groupby(result.index.date)
    result = grouped.agg(
        {
            f"Top price before {close}": "first",
            f"Low price before {close}": "first",
            f"End price at {close}": "first",
            "Price at eod": "last",
        },
    ).dropna()

    print(result)

    gaps = {}
    previous_day = None
    for index, row in result.iterrows():
        if previous_day is not None:
            gaps[previous_day] = {
                "high": row[f"Top price before {close}"] - result.loc[previous_day]["Price at eod"],
                "low": row[f"Low price before {close}"] - result.loc[previous_day]["Price at eod"],
                "close": row[f"End price at {close}"] - result.loc[previous_day]["Price at eod"],
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


def test_hold(settings):
    from pprint import pprint

    period_days = 90

    side = "BULL"

    times = pd.date_range(start="09:00", end="17:00", freq="5min").time
    buy_time_sell_time_combinations = [
        (buy_time, sell_time) for buy_time in times for sell_time in times if buy_time < sell_time
    ]

    result_for_intervals = {}
    for buy_time, sell_time in buy_time_sell_time_combinations:
        result_for_intervals[(buy_time, sell_time)] = []

        data = Storage(settings).read()
        data = data.loc[
            data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
        ]
        data.index = pd.to_datetime(data.index)
        daily_data = data.resample("D")

        price_at_buy_time = daily_data["Close"].apply(lambda x: x.at_time(buy_time))
        price_at_sell_time = daily_data["Close"].apply(lambda x: x.at_time(sell_time))

        high_between_buy_and_sell_times = daily_data["High"].apply(
            lambda x: x[(x.index.time >= buy_time) & (x.index.time <= sell_time)].max(),
        )
        low_between_buy_and_sell_times = daily_data["Low"].apply(
            lambda x: x[(x.index.time >= buy_time) & (x.index.time <= sell_time)].min(),
        )

        result = pd.DataFrame(
            {
                "buy": price_at_buy_time,
                "sell": price_at_sell_time,
                "high": high_between_buy_and_sell_times,
                "low": low_between_buy_and_sell_times,
            },
        )
        result.index = pd.to_datetime(result.index)
        grouped = result.groupby(result.index.date)

        result = grouped.agg(
            {
                "buy": "first",
                "sell": "first",
                "high": "first",
                "low": "first",
            },
        ).dropna()

        # print(result)

        for cut_off in range(5, 50, 2):
            counter = 0
            total = 0
            for i, row in result.iterrows():
                if (side == "BULL" and (row["high"] - row["buy"] > cut_off)) or (
                    side == "BEAR" and (row["buy"] - row["low"] > cut_off)
                ):
                    # print("CUT_OFF", i, row["buy"], row["low" if side == "BEAR" else "high"])
                    total += cut_off
                    counter += 1

                else:
                    profit = (row["sell"] - row["buy"]) * (1 if side == "BULL" else -1)
                    total += profit
                    if profit > 0:
                        # print("TIMEOUT", i, row["buy"], row["sell"])
                        counter += 1

            if result.shape[0] == 0:
                continue

            efficiency = round(counter / result.shape[0], 2)
            if efficiency > 0.5 and total > 0:
                result_for_intervals[(buy_time, sell_time)].append((cut_off, efficiency, round(total, 2)))

            # print(cut_off, round(counter / result.shape[0], 2), round(total, 2))

    pprint(result_for_intervals)

    print("(-----------")
    reformed_results = [
        (interval, sorted(efficiencies, key=lambda x: x[1] * x[2], reverse=True)[0])
        for interval, efficiencies in result_for_intervals.items()
        if efficiencies
    ]

    pprint(sorted(reformed_results, key=lambda x: x[1][1] * x[1][2], reverse=True))


if __name__ == "__main__":
    run_full_strategies_generation(SETTINGS_TRADE_OMX)
    # run_test_for_selected_indicators(SETTINGS_TRADE_OMX)
    # run_plotting_for_active_strategies(SETTINGS_TRADE_OMX)

    # test_gaps(SETTINGS_TRADE_OMX)
    # test_hold(SETTINGS_TRADE_OMX)
