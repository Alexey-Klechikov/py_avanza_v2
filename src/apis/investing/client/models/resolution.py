from enum import Enum


class Resolution(Enum):
    ONE_MINUTE = "1"
    FIVE_MINUTES = "5"
    FIFTEEN_MINUTES = "15"
    THIRTY_MINUTES = "30"
    FOURTY_FIVE_MINUTES = "45"
    SIXTY_MINUTES = "60"
    DAY = "D"
    WEEK = "W"
    MONTH = "M"

    @property
    def mins(self):
        return int(self.value)
