from enum import Enum


class Direction(Enum):
    """Which product family a position is held in: BULL instruments rise with the index, BEAR instruments fall."""

    BULL = "BULL"
    BEAR = "BEAR"

    def __str__(self):
        return self.value


class FlowAction(Enum):
    TRADE = "TRADE"
    DO_NOTHING = "DO_NOTHING"
    EXIT_TRADING = "EXIT_TRADING"
