import json
import os
import pickle
import warnings
from dataclasses import dataclass
from datetime import timedelta
from pprint import pprint

import pandas as pd

from apis.avanza.operators.search import get_all_nordic_stocks
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


def _get_data(period_days: int):
    data = Storage().read()
    data = data.loc[(data.index >= TODAY_MIDNIGHT - timedelta(days=period_days)) & (data.index < TODAY_MIDNIGHT)]
    data.index = pd.to_datetime(data.index)

    return data


def run_strategies_generation(period_days: int, full: bool, comment: str | None = None):
    if full:
        log.warning("Generating strategies")
        backtest_trade_strategies(
            _get_data(period_days + 20),
            ComposeStrategiesListMethod.GENERATE,
            strategies_file_name_suffix_new="dev_3",
        )

        for i in range(3, SETTINGS.STRATEGY.INDICATORS):
            log.warning(f"Extending strategies ({i} -> {i + 1})")
            backtest_trade_strategies(
                _get_data(period_days + 20),
                ComposeStrategiesListMethod.EXTEND,
                strategies_file_name_suffix_old=f"dev_{i}",
                strategies_file_name_suffix_new=f"dev_{i + 1}",
            )

    log.warning("Backtesting strategies")
    backtest_trade_strategies(
        _get_data(period_days),
        ComposeStrategiesListMethod.READ,
        strategies_file_name_suffix_old=f"dev_{SETTINGS.STRATEGY.INDICATORS}",
        strategies_file_name_suffix_new=comment,
    )


def run_plotting_for_active_strategies(period_days: int):
    backtest_trade_strategies(
        _get_data(period_days),
        ComposeStrategiesListMethod.READ,
        plot=True,
    )


def _generate_tested_kwargs() -> TestedKwargs:
    tested_kwargs = TestedKwargs(indicator_to_test=("Volatility", "STARC"), kwargs=[])

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
    for length_1 in range(6, 14, 2):
        for length_2 in range(length_1, 16, 2):
            for length_3 in range(18, 24, 2):
                #     # for threshold in range(57, 61, 2):
                if length_1 == length_2:
                    continue

                kwargs = {"length_ma": length_1, "length_atr": length_2, "multiplier_atr": length_3 / 10, "mamode": "wma"}

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
            _get_data(period_days),
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


def get_all_stocks():
    file = "src/data/avanza_stocks_list.pickle"
    if not os.path.exists(file):
        stocks_list = get_all_nordic_stocks()
        df = pd.DataFrame([i.model_dump() for i in stocks_list])
        pickle.dump(df, open(file, "wb"))
    else:
        df = pickle.load(open(file, "rb"))

    pprint(df.columns)

    # df.fillna(0, inplace=True)
    df.drop(columns=["currency", "type"], inplace=True)
    df = df[
        (df["price_earnings_ratio"] > 0)
        & (df["earnings_per_share"] > 0)
        & (df["direct_yield"] > 0)
        # & (df["dividends_per_year"] > 0)
        & (df["five_years_change_percent"] > 0)
        & (df["one_year_change_percent"] > 0)
        & (df["three_years_change_percent"] > 0)
        # & (df["next_dividend"] > date.today())
        & (df["sma20"] > 0)
        & (df["sma50"] > 0)
        & (df["sma200"] > 0)
        & (df["market_capitalization"] > 10000)
        & (df["rsi_trend_three_days"] > 0)
        & (df["rsi_trend_five_days"] > 0)
        & (df["one_month_change_percent"] > 0.02)
        & (df["one_week_change_percent"] > 0.01)
        & (df["rsi14"] < 75)
    ]
    df["dividend_ratio"] = df["dividend_per_share"] / df["buy_price"]
    df.sort_values(by=["price_earnings_ratio"], ascending=False, inplace=True)
    # df = df[(df["dividend_ratio"] > 0.02)]
    # df = df.loc[df.groupby("next_dividend")["dividend_ratio"].idxmax()]
    print(
        df[
            [
                "name",
                "country_code",
                "return_on_equity",
                "price_earnings_ratio",
                "earnings_per_share",
                "net_debt_ebitda_ratio",
                "direct_yield",
                "dividends_per_year",
                "price_book_ratio",
                "equity_per_share",
                "ev_ebit_ratio",
                "market_capitalization",
                "next_dividend",
                "dividend_ratio",
                "short_selling_ratio",
                "buy_price",
                "sma20",
                "sma50",
                "sma200",
                "rsi14",
                "rsi_trend_three_days",
                "rsi_trend_five_days",
                "one_month_change_percent",
                "beta",
            ]
        ].reset_index(),
    )


if __name__ == "__main__":
    # run_strategies_generation(period_days=80, full=True)
    # run_test_for_selected_indicators(period_days=60)
    # run_plotting_for_active_strategies(period_days=5)
    # get_statistics_per_indicator()

    get_all_stocks()
