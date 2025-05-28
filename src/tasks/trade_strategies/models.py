from enum import Enum


class Signal(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    EXIT = "EXIT"


class FlowAction(Enum):
    TRADE = "TRADE"
    DO_NOTHING = "DO_NOTHING"
    EXIT_TRADING = "EXIT_TRADING"
