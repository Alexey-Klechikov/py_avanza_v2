from enum import Enum

from pydantic import BaseModel

from services.ta.indicators.models import Indicator
from utils.logger import get_logger

log = get_logger()


class ComposeStrategiesListMethod(Enum):
    READ = "READ"
    GENERATE = "GENERATE"
    EXTEND = "EXTEND"


class Counter(BaseModel):
    total_trades: int = 0
    total_profit: float = 0
    profitable_trades: int = 0


class Strategy:
    def __init__(
        self,
        indicators_mapping: dict[str, dict[str, Indicator]],
        selected_indicators: list[tuple[str, str]],
        original: bool = False,
    ):
        self.counter = Counter()
        self.selected_indicators = selected_indicators
        self.indicators_logic: list[Indicator] = []

        components = []
        for category, name in selected_indicators:
            indicator = indicators_mapping.get(category, {}).get(name)
            if not indicator:
                log.warning(f"Indicator {name} from category {category} does not exist.")
                continue

            if indicator.plots is None:
                log.warning(f"Indicator {name}-{category} does not have any plots.")
                continue

            components.append(f"{category}-{name}")
            self.indicators_logic.append(indicator)

        self.name = " | ".join(sorted(components)) + (" | Original" if original else "")
