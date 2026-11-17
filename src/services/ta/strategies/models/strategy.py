from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

from services.ta.indicators.models.indicator import Indicator
from utils.logger.operators import get_logger

log = get_logger()


class ComposeStrategiesListMethod(Enum):
    READ = "READ"
    GENERATE = "GENERATE"
    EXTEND = "EXTEND"


class TradeStats(BaseModel):
    """Closed-trade results of one strategy (or of the replayed live selection)."""

    total_trades: int = 0
    total_profit: float = 0  # underlying points
    profitable_trades: int = 0
    # (close date, capital return) per closed trade, for recency-weighted daily scoring
    trade_returns: list[tuple[date, float]] = Field(default_factory=list)

    @property
    def profitable_share(self) -> float:
        return self.profitable_trades / self.total_trades if self.total_trades else 0.0

    def record(self, profit: float, capital_return: float, closed_on: date) -> None:
        self.total_trades += 1
        self.total_profit += profit
        self.profitable_trades += 1 if profit > 0 else 0
        self.trade_returns.append((closed_on, capital_return))


class Strategy:
    def __init__(
        self,
        indicators_mapping: dict[str, dict[str, Indicator]],
        selected_indicators: list[tuple[str, str]],
        original: bool = False,
        efficiency: float = 0,
        rank: int = 0,
    ):
        self.trade_stats = TradeStats()
        self.original = original
        self.selected_indicators = selected_indicators
        self.indicators_logic: list[Indicator] = []
        self.efficiency = efficiency
        self.rank = rank

        components = []
        for category, name in selected_indicators:
            indicator = indicators_mapping.get(category, {}).get(name)
            if not indicator:
                # log.warning(f"Indicator {name} from category {category} does not exist.")
                continue

            if indicator.plots is None:
                log.warning(f"Indicator {name}-{category} does not have any plots.")
                continue

            components.append(f"{category}-{name}")
            self.indicators_logic.append(indicator)

        self.components_name = " | ".join(sorted(components))

    @property
    def name(self) -> str:
        return self.components_name + (" | Original" if self.original else "")
