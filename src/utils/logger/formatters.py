import copy
import logging


class OneLineFormatter(logging.Formatter):
    def __init__(
        self,
        fmt="[%(levelname)s] [%(asctime)s] [%(name)s] - %(message)s",
        datefmt="%H:%M:%S",
    ):
        super().__init__(fmt, datefmt)
        self.displacements = {
            0: {"type": "time", "size": 8},
            1: {"type": "logger", "size": 9},
            2: {"type": "message", "size": 35},
        }

    def format(self, record) -> str:
        s = super().format(record)
        s = (
            s.replace("\n", " >>>")
            .replace("main.", "")
            .replace("Signal.LONG", "🟢 LONG")
            .replace("Signal.SHORT", "🔴 SHORT")
        )

        if s.find("Done"):
            s = s.split("--")[0]

        for i, block in enumerate(s.split("]")[:3]):
            s = s.replace(
                f"{block}]",
                f"{block}]" + (" " * (self.displacements[i]["size"] - len(block))),
            )

            if self.displacements[i]["type"] == "message":
                self.displacements[i]["size"] = max(
                    len(block),
                    self.displacements[i]["size"],
                )

        return s


class ColoredFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    MAPPING = {
        "DEBUG": 37,  # white
        "INFO": 38,  # grey
        "WARNING": 33,  # yellow
        "ERROR": 31,  # red
        "CRITICAL": 41,
    }  # white on red bg

    PREFIX = "\033["
    SUFFIX = "\033[0m"

    def __init__(self, pattern: str) -> None:
        logging.Formatter.__init__(self, pattern)

        self.messages_counter = 0

    def format(self, record) -> str:
        colored_record = copy.copy(record)
        levelname = colored_record.levelname
        colored_levelname = f"{self.PREFIX}{self.MAPPING.get(levelname, 38)}m{levelname}{self.SUFFIX}"
        colored_record.levelname = colored_levelname

        s = logging.Formatter.format(self, colored_record)
        s = s.replace("main.", "").replace("Signal.LONG", "🟢 LONG").replace("Signal.SHORT", "🔴 SHORT")

        self.messages_counter += 1

        return s
