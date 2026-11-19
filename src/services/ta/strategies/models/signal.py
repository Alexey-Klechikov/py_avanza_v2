from enum import Enum


class Signal(Enum):
    LONG = "LONG"
    SHORT = "SHORT"

    @classmethod
    def from_bar(cls, long: bool, short: bool) -> "Signal | None":
        """Conflicting LONG and SHORT cancel out. Same rule in the backtest and live."""
        if long and not short:
            return cls.LONG

        if short and not long:
            return cls.SHORT

        return None
