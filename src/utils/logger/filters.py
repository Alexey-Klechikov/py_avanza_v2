import logging

LEVEL_NUMBERS = {"DEBUG": logging.DEBUG, "INFO": logging.INFO, "WARNING": logging.WARNING, "ERROR": logging.ERROR}


class LevelFilter(logging.Filter):
    """Passes records from the first to the second level name of `log_levels`, both inclusive."""

    def __init__(self, log_levels: tuple) -> None:
        super().__init__()
        self._lowest_level = LEVEL_NUMBERS[log_levels[0]]
        self._highest_level = LEVEL_NUMBERS[log_levels[1]]

    def filter(self, record: logging.LogRecord) -> bool:
        return self._lowest_level <= record.levelno <= self._highest_level
