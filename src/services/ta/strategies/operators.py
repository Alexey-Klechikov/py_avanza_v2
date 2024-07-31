import json
import os
import warnings
from copy import deepcopy
from typing import Dict, List, Optional, Tuple

from services.ta.indicators.models import Indicator
from services.ta.strategies.models import ComposeStrategiesListMethod, Strategy
from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)


log = get_logger()


def _get_file_path(filename: Optional[str]) -> str:
    current_file_path = os.path.abspath(__file__)
    root_dir = "/src" if "/src" in current_file_path else "/pyAvanza"
    return current_file_path.split(root_dir)[0] + f"{root_dir}/data/{filename}"


def _generate_strategies(
    indicators_selector: List[Tuple[str, str]],
    indicators: Dict[str, Dict[str, Indicator]],
) -> List[Strategy]:
    strategies: List[Strategy] = []
    for i1, indicator1 in enumerate(indicators_selector):
        if len(indicators_selector) == 1:
            strategies.append(
                deepcopy(
                    Strategy(
                        name=" | ".join([f"{category}-{indicator}" for category, indicator in (indicator1,)]),
                        selected_indicators=[indicator1],
                        all_indicators=indicators,
                    ),
                ),
            )

        for i2, indicator2 in enumerate(indicators_selector[i1 + 1 :]):
            if len(indicators_selector) <= 2:
                strategies.append(
                    deepcopy(
                        Strategy(
                            name=" | ".join(
                                [f"{category}-{indicator}" for category, indicator in (indicator1, indicator2)],
                            ),
                            selected_indicators=[indicator1, indicator2],
                            all_indicators=indicators,
                        ),
                    ),
                )

            for _, indicator3 in enumerate(indicators_selector[i1 + i2 + 2 :]):
                strategies.append(
                    deepcopy(
                        Strategy(
                            name=" | ".join(
                                [
                                    f"{category}-{indicator}"
                                    for category, indicator in (indicator1, indicator2, indicator3)
                                ],
                            ),
                            selected_indicators=[indicator1, indicator2, indicator3],
                            all_indicators=indicators,
                        ),
                    ),
                )

    return strategies


def _extend_strategies(
    indicators_selector: List[Tuple[str, str]],
    indicators: Dict[str, Dict[str, Indicator]],
    old_strategies_file_path: str,
) -> List[Strategy]:
    extended_strategies: List[Strategy] = []
    for strategy in json.load(open(old_strategies_file_path)):
        if "Original" in strategy["name"]:
            continue

        strategy_indicators = set(tuple(indicator.split("-")) for indicator in strategy["name"].split(" | "))

        extended_strategies.append(
            deepcopy(
                Strategy(
                    name=f'{strategy["name"]} | Original',
                    selected_indicators=list(strategy_indicators),
                    all_indicators=indicators,
                ),
            ),
        )

        for category, indicator in indicators_selector:
            if (category, indicator) in strategy_indicators:
                continue

            if set(list(strategy_indicators) + [(category, indicator)]) in [
                set(i.selected_indicators) for i in extended_strategies
            ]:
                continue

            extended_strategies.append(
                deepcopy(
                    Strategy(
                        name=f"{strategy['name']} | {category}-{indicator}",
                        selected_indicators=list(strategy_indicators) + [(category, indicator)],
                        all_indicators=indicators,
                    ),
                ),
            )

    return extended_strategies


def _read_strategies(indicators: Dict[str, Dict[str, Indicator]], old_strategies_file_path: str):
    old_strategies: List[Strategy] = []
    for strategy in json.load(open(old_strategies_file_path)):
        if "Original" in strategy["name"]:
            continue

        strategy_indicators = list(tuple(indicator.split("-")) for indicator in strategy["name"].split(" | "))

        old_strategies.append(
            deepcopy(
                Strategy(name=strategy["name"], selected_indicators=strategy_indicators, all_indicators=indicators),
            ),
        )

    return old_strategies


def compose_strategies_list(
    method: ComposeStrategiesListMethod,
    indicators: Dict[str, Dict[str, Indicator]],
    indicators_selector: List[Tuple[str, str]],
    old_strategies_file_name: Optional[str] = None,
) -> List[Strategy]:
    if method == ComposeStrategiesListMethod.GENERATE and len(indicators_selector) > 0:
        strategies = _generate_strategies(indicators_selector, indicators)

    elif method == ComposeStrategiesListMethod.EXTEND and old_strategies_file_name:
        strategies = _extend_strategies(indicators_selector, indicators, _get_file_path(old_strategies_file_name))

    elif method == ComposeStrategiesListMethod.READ and old_strategies_file_name:
        strategies = _read_strategies(indicators, _get_file_path(old_strategies_file_name))

    else:
        raise ValueError("Can not compose list of strategies - invalid method or missing arguments.")

    return strategies


def dump_strategies_in_file(strategies: List[Strategy], new_strategies_file_name: str):
    rank = 1
    strategies_for_file = []
    for strategy in strategies:
        if rank > 100 or strategy.counter.total_profit <= 0:
            break

        if "Original" in strategy.name:
            continue

        strategies_for_file.append(
            {
                "rank": rank,
                "name": strategy.name,
                "total_trades": strategy.counter.total_trades,
                "total_profit": round(strategy.counter.total_profit, 2),
                "profitable_trades_share": (
                    round(strategy.counter.profitable_trades / strategy.counter.total_trades, 2)
                    if strategy.counter.profitable_trades > 0
                    else 0
                ),
            },
        )

        rank += 1

    json.dump(strategies_for_file, open(_get_file_path(new_strategies_file_name), "w"), indent=4)


def get_top_strategy(indicators: Dict[str, Dict[str, Indicator]], strategies_file_name: str) -> Strategy:
    top_strategy = json.load(open(_get_file_path(strategies_file_name)))[0]
    strategy_indicators = list(tuple(indicator.split("-")) for indicator in top_strategy["name"].split(" | "))

    return Strategy(name=top_strategy["name"], selected_indicators=strategy_indicators, all_indicators=indicators)
