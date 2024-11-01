import datetime
import inspect
import logging
import os
from logging import Logger

from utils.logger.filters import LevelFilter
from utils.logger.formatters import ColoredFormatter, OneLineFormatter


def _get_log_file_name(file_prefix: str) -> str:
    log_dir = os.path.join("/".join(os.path.abspath(__file__).split("/")[:-3]), "logs")
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)

    return f"{log_dir}/{file_prefix}"


def _create_console_handler(log: Logger, log_levels: tuple) -> None:
    ch = logging.StreamHandler()
    ch.addFilter(LevelFilter(log_levels))
    cf = ColoredFormatter("[%(levelname)s] [%(name)s] - %(message)s")
    ch.setFormatter(cf)
    log.addHandler(ch)


def _create_file_handler(
    log: Logger,
    file_name: str,
    log_levels: tuple,
    write_mode: str,
    datefmt="%H:%M:%S",
) -> None:
    fh = logging.FileHandler(file_name, write_mode)
    fh.addFilter(LevelFilter(log_levels))
    ff = OneLineFormatter(datefmt=datefmt)
    fh.setFormatter(ff)
    log.addHandler(fh)


def _remove_handlers(log: Logger, handler_type: type) -> None:
    handlers_to_remove = [h for h in log.handlers if isinstance(h, handler_type)]
    for handler in handlers_to_remove:
        log.removeHandler(handler)
        handler.close()


def set_handlers(
    file_prefix: str,
    console_log_levels: tuple = ("DEBUG", "WARNING"),
) -> None:
    log = logging.getLogger("main")
    log_file_name = _get_log_file_name(file_prefix)

    _create_console_handler(log, console_log_levels)

    _create_file_handler(
        log,
        file_name=f"{log_file_name}_{datetime.datetime.now():%Y-%m-%d}.log",
        log_levels=("INFO", "WARNING"),
        write_mode="a",
    )

    _create_file_handler(
        log,
        file_name=f"{log_file_name}_DEBUG.log",
        log_levels=("DEBUG", "WARNING"),
        write_mode="w",
    )

    _create_file_handler(
        log,
        file_name=f"{log_file_name}_ERROR.log",
        log_levels=("ERROR", "ERROR"),
        write_mode="a",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    log.setLevel(os.environ.get("LOGLEVEL", "DEBUG"))


def reset_file_handlers(
    file_prefix: str,
):
    log = logging.getLogger("main")
    log_file_name = _get_log_file_name(file_prefix)

    _remove_handlers(log, logging.FileHandler)

    _create_file_handler(
        log,
        file_name=f"{log_file_name}.log",
        log_levels=("INFO", "WARNING"),
        write_mode="a",
    )

    log.warning("#########################################################")


def get_logger() -> Logger:
    caller_frame = inspect.stack()[1]
    root_dir = "/src/" if "/src/" in caller_frame.filename else "pyAvanza/"
    logger_name = caller_frame.filename.split(root_dir)[1].replace(".py", "").replace("/", ".")

    return logging.getLogger(f"main.{logger_name}")
