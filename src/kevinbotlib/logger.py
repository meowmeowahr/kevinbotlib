from dataclasses import dataclass
from enum import Enum
from typing import IO

from loguru import logger as _internal_logger


class Level(Enum):
    DATA = _internal_logger.level("DATA", no=4, color="<magenta>", icon="🔄")
    TRACE = _internal_logger.level("TRACE")
    DEBUG = _internal_logger.level("DEBUG")
    INFO = _internal_logger.level("INFO")
    WARNING = _internal_logger.level("WARNING")
    ERROR = _internal_logger.level("ERROR")
    CRITICAL = _internal_logger.level("CRITICAL")

@dataclass
class LoggerWriteOpts:
    depth: int = 2

class Logger:
    def __init__(self, level: Level = Level.DEBUG) -> None:
        # TODO: implement levels
        self._internal_logger = _internal_logger
        self.level = level

    def log(self, level: Level, message: str, opts: LoggerWriteOpts = LoggerWriteOpts()):
        """Log a message with a specified level

        Args:
            level (Level): Level to log at
            message (str): Message to log
        """
        _internal_logger.opt(depth=opts.depth).log(level.value.name, message)

    def trace(self, message: str):
        _internal_logger.opt(depth=1).log(Level.TRACE.name, message)

    def debug(self, message: str):
        _internal_logger.opt(depth=1).log(Level.DEBUG.name, message)

    def info(self, message: str):
        _internal_logger.opt(depth=1).log(Level.INFO.name, message)

    def warning(self, message: str):
        _internal_logger.opt(depth=1).log(Level.WARNING.name, message)

    def warn(self, message: str):
        _internal_logger.opt(depth=1).log(Level.WARNING.name, message)

    def error(self, message: str):
        _internal_logger.opt(depth=1).log(Level.ERROR.name, message)

    def critical(self, message: str):
        _internal_logger.opt(depth=1).log(Level.CRITICAL.name, message)

class StreamRedirector(IO):

    def __init__(self, logger: Logger, level: Level = Level.INFO):
        self._level = level
        self._logger = logger

    def write(self, buffer):
        for line in buffer.rstrip().splitlines():
            self._logger.log(self._level, line.rstrip())

    def flush(self):
        pass