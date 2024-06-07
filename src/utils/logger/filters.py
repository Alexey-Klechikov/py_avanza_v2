import logging


class LevelFilter(logging.Filter):
    def __init__(self, log_levels: tuple):
        log_level_to_int = {
            "DEBUG": 10,
            "INFO": 20,
            "WARNING": 30,
            "ERROR": 40,
        }

        self._low = log_level_to_int[log_levels[0]]
        self._high = log_level_to_int[log_levels[1]]
        logging.Filter.__init__(self)

    def filter(self, record):
        return self._low <= record.levelno <= self._high
