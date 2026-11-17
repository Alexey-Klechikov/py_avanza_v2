from enum import Enum


class Signal(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    EXIT = "EXIT"

    @classmethod
    def from_bar(cls, long: bool, short: bool, exit: bool) -> "Signal | None":
        """EXIT wins over entries; conflicting LONG and SHORT cancel out. Same rule in the backtest and live."""
        if exit:
            return cls.EXIT

        if long and not short:
            return cls.LONG

        if short and not long:
            return cls.SHORT

        return None
