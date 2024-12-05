import json
import os
import warnings
from copy import deepcopy

from services.ta.indicators.models import Indicator
from services.ta.strategies.models import ComposeStrategiesListMethod, Strategy
from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)


log = get_logger()


def _get_file_path(filename: str | None) -> str:
    filename = f"trade_strategies_{filename}.json" if filename else "trade_strategies.json"
    current_file_path = os.path.abspath(__file__)
    root_dir = "/src" if "/src" in current_file_path else "/pyAvanza"
    return current_file_path.split(root_dir)[0] + f"{root_dir}/config/{filename}"


def _generate_strategies(indicators_mapping: dict[str, dict[str, Indicator]]) -> list[Strategy]:
    strategies: list[Strategy] = []

    indicators = [
        (category, indicator) for category, indicators in indicators_mapping.items() for indicator in indicators.keys()
    ]

    for i1, indicator1 in enumerate(indicators):
        if len(indicators) == 1:
            strategies.append(
                deepcopy(
                    Strategy(
                        selected_indicators=[indicator1],
                        indicators_mapping=indicators_mapping,
                    ),
                ),
            )

        for i2, indicator2 in enumerate(indicators[i1 + 1 :]):
            if len(indicators) <= 2:
                strategies.append(
                    deepcopy(
                        Strategy(
                            selected_indicators=[indicator1, indicator2],
                            indicators_mapping=indicators_mapping,
                        ),
                    ),
                )

            for _, indicator3 in enumerate(indicators[i1 + i2 + 2 :]):
                strategies.append(
                    deepcopy(
                        Strategy(
                            selected_indicators=[indicator1, indicator2, indicator3],
                            indicators_mapping=indicators_mapping,
                        ),
                    ),
                )

    return strategies


def _extend_strategies(
    indicators_mapping: dict[str, dict[str, Indicator]],
    old_strategies_file_path: str,
) -> list[Strategy]:
    extended_strategies: list[Strategy] = []

    indicators = [
        (category, indicator) for category, indicators in indicators_mapping.items() for indicator in indicators.keys()
    ]

    for strategy in json.load(open(old_strategies_file_path)):
        if "Original" in strategy["name"]:
            continue

        strategy_indicators = {tuple(indicator.split("-")) for indicator in strategy["name"].split(" | ")}

        extended_strategies.append(
            deepcopy(
                Strategy(
                    original=True,
                    selected_indicators=list(strategy_indicators),
                    indicators_mapping=indicators_mapping,
                ),
            ),
        )

        for category, indicator in indicators:
            if (category, indicator) in strategy_indicators:
                continue

            if set(list(strategy_indicators) + [(category, indicator)]) in [
                set(i.selected_indicators) for i in extended_strategies
            ]:
                continue

            extended_strategies.append(
                deepcopy(
                    Strategy(
                        selected_indicators=list(strategy_indicators) + [(category, indicator)],
                        indicators_mapping=indicators_mapping,
                    ),
                ),
            )

    return extended_strategies


def _read_strategies(indicators_mapping: dict[str, dict[str, Indicator]], old_strategies_file_path: str):
    old_strategies: list[Strategy] = []
    for strategy in json.load(open(old_strategies_file_path)):
        if "Original" in strategy["name"]:
            continue

        strategy_indicators = list(tuple(indicator.split("-")) for indicator in strategy["name"].split(" | "))

        old_strategies.append(
            deepcopy(
                Strategy(selected_indicators=strategy_indicators, indicators_mapping=indicators_mapping),
            ),
        )

    return old_strategies


def compose_strategies_list(
    method: ComposeStrategiesListMethod,
    indicators_mapping: dict[str, dict[str, Indicator]],
    old_strategies_file_name: str | None = None,
) -> list[Strategy]:
    if method == ComposeStrategiesListMethod.GENERATE:
        strategies = _generate_strategies(indicators_mapping)

    elif method == ComposeStrategiesListMethod.EXTEND and old_strategies_file_name:
        strategies = _extend_strategies(indicators_mapping, _get_file_path(old_strategies_file_name))

    elif method == ComposeStrategiesListMethod.READ and old_strategies_file_name:
        strategies = _read_strategies(indicators_mapping, _get_file_path(old_strategies_file_name))

    else:
        raise ValueError("Can not compose list of strategies - invalid method or missing arguments.")

    return strategies


def dump_strategies_in_file(strategies: list[Strategy], new_strategies_file_name: str | None):
    rank = 1
    last_strategy_stats = ""
    strategies_for_file = []
    for strategy in strategies:
        strategy_candidate = {
            "rank": rank,
            "name": strategy.name,
            "total_trades": strategy.counter.total_trades,
            "total_profit": round(strategy.counter.total_profit, 2),
            "profitable_trades_share": (
                round(strategy.counter.profitable_trades / strategy.counter.total_trades, 2)
                if strategy.counter.profitable_trades > 0
                else 0
            ),
        }

        current_strategy_stats = " | ".join(
            [
                str(v)
                for k, v in strategy_candidate.items()
                if k in ["total_trades", "total_profit", "profitable_trades_share"]
            ],
        )
        if current_strategy_stats == last_strategy_stats:
            continue
        last_strategy_stats = current_strategy_stats

        if rank > 200 or strategy_candidate["total_profit"] <= 0:
            break

        if "Original" in strategy_candidate["name"]:
            continue

        strategies_for_file.append(strategy_candidate)

        rank += 1

    json.dump(strategies_for_file, open(_get_file_path(new_strategies_file_name), "w"), indent=2, sort_keys=True)


def get_top_strategies(
    indicators_mapping: dict[str, dict[str, Indicator]],
    strategies_file_name: str | None,
) -> list[Strategy]:
    top_strategies = sorted(
        json.load(open(_get_file_path(strategies_file_name)))[:10],
        key=lambda x: x["profitable_trades_share"],
        reverse=True,
    )[:5]

    return [
        Strategy(
            selected_indicators=list(tuple(indicator.split("-")) for indicator in i["name"].split(" | ")),
            indicators_mapping=indicators_mapping,
            efficiency=i["profitable_trades_share"],
        )
        for i in top_strategies
    ]
