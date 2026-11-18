from services.ta.indicators.models.indicator import Indicator
from utils.logger.operators import get_logger

log = get_logger()


class Strategy:
    """Indicators whose signals combine: LONG/SHORT when all agree, EXIT when any signals (see signals.py)."""

    def __init__(
        self,
        indicators_mapping: dict[str, dict[str, Indicator]],
        selected_indicators: list[tuple[str, str]],
    ):
        self.selected_indicators = selected_indicators
        self.indicators_logic: list[Indicator] = []

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
        return self.components_name
