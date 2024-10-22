from enum import Enum


class Direction(Enum):
    BULL = "BULL"
    BEAR = "BEAR"

    def __str__(self):
        return self.value
