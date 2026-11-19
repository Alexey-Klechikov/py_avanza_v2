import copy
import logging

COLOR_CODE_BY_LEVEL = {"DEBUG": 37, "INFO": 38, "WARNING": 33, "ERROR": 31, "CRITICAL": 41}


def _shorten(message: str) -> str:
    return message.replace("main.", "").replace("Signal.LONG", "🟢 LONG").replace("Signal.SHORT", "🔴 SHORT")


class OneLineFormatter(logging.Formatter):
    def __init__(self, fmt="[%(levelname)s] [%(asctime)s] [%(name)s] - %(message)s", datefmt="%H:%M:%S"):
        super().__init__(fmt, datefmt)
        # Padded widths of the time, logger and message blocks; the message width grows to the widest seen
        self.block_widths = [8, 9, 35]

    def format(self, record: logging.LogRecord) -> str:
        line = _shorten(super().format(record).replace("\n", " >>>"))

        blocks = line.split("]")[:3]
        for position, block in enumerate(blocks):
            line = line.replace(f"{block}]", f"{block}]" + " " * (self.block_widths[position] - len(block)))

        if len(blocks) == 3:
            self.block_widths[2] = max(len(blocks[2]), self.block_widths[2])

        return line


class ColoredFormatter(logging.Formatter):
    """Colors the level name with its ANSI code."""

    def format(self, record: logging.LogRecord) -> str:
        colored_record = copy.copy(record)
        color_code = COLOR_CODE_BY_LEVEL.get(record.levelname, 38)
        colored_record.levelname = f"\033[{color_code}m{record.levelname}\033[0m"

        return _shorten(super().format(colored_record))
