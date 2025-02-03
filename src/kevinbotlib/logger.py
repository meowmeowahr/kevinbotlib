from enum import Enum
from loguru import logger as _internal_logger

class Level(Enum):
    TRACE = _internal_logger.level("TRACE")
    DEBUG = _internal_logger.level("DEBUG")
    INFO = _internal_logger.level("INFO")
    WARNING = _internal_logger.level("WARNING")
    ERROR = _internal_logger.level("ERROR")
    CRITICAL = _internal_logger.level("CRITICAL")


class Logger:
    def __init__(self) -> None:
        pass

    def log(self, level: Level, message: str):
        """Log a message with a specified level

        Args:
            level (Level): Level to log at
            message (str): Message to log
        """
        _internal_logger.opt(depth=1).log(level.value.name, message)

    def trace(self, message: str):
        self.log(Level.TRACE, message)

    def debug(self, message: str):
        self.log(Level.DEBUG, message)

    def info(self, message: str):
        self.log(Level.INFO, message)

    def warning(self, message: str):
        self.log(Level.WARNING, message)

    def warn(self, message: str):
        self.log(Level.WARNING, message)

    def error(self, message: str):
        self.log(Level.ERROR, message)

    def critical(self, message: str):
        self.log(Level.CRITICAL, message)
