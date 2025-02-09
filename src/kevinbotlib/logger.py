from dataclasses import dataclass
from enum import Enum
from typing import IO
import os
import glob
from datetime import datetime
from zipfile import ZipFile
import platformdirs
from loguru import logger as _internal_logger


class LoggerDirectories:
    @staticmethod
    def get_logger_directory(ensure_exists=True) -> str:
        """Returns the log directory path and ensures its existence if needed."""
        log_dir = platformdirs.user_data_dir("kevinbotlib/logging", ensure_exists=ensure_exists)
        os.makedirs(log_dir, exist_ok=True)
        return log_dir

    @staticmethod
    def cleanup_logs(directory: str, max_size_mb: int = 500):
        """Deletes oldest log files if the total log directory exceeds max_size_mb."""
        log_files = sorted(glob.glob(os.path.join(directory, "*.log")), key=os.path.getctime)

        while log_files and LoggerDirectories.get_directory_size(directory) > max_size_mb:
            os.remove(log_files.pop(0))  # Delete oldest file

    @staticmethod
    def get_directory_size(directory: str) -> float:
        """Returns the size of the directory in MB."""
        return sum(os.path.getsize(f) for f in glob.glob(os.path.join(directory, "*.log"))) / (1024 * 1024)


class Level(Enum):
    DATA = _internal_logger.level("DATA", no=3, color="<magenta>", icon="🔄")
    TRACE = _internal_logger.level("TRACE")
    HIGHFREQ = _internal_logger.level("HIGHFREQ", no=7, color="<magenta>", icon="⏩")
    DEBUG = _internal_logger.level("DEBUG")
    INFO = _internal_logger.level("INFO")
    WARNING = _internal_logger.level("WARNING")
    ERROR = _internal_logger.level("ERROR")
    CRITICAL = _internal_logger.level("CRITICAL")


@dataclass
class LoggerWriteOpts:
    depth: int = 1
    colors: bool = True
    ansi: bool = True


class Logger:
    def __init__(self, level: Level = Level.DEBUG) -> None:
        self._internal_logger = _internal_logger
        self.level = level

    @property
    def loguru_logger(self):
        return self._internal_logger

    def configure_file_logger(self, directory: str, rotation_size: str = "150MB") -> str:
        """Configures file-based logging with rotation and cleanup."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]  # Trim to milliseconds

        log_file = os.path.join(directory, f"{timestamp}.log")
        self._internal_logger.add(
            log_file,
            rotation=rotation_size,
            compression="zip",
            enqueue=True,
            serialize=True
        )
        return log_file

    def log(self, level: Level, message: str, opts: LoggerWriteOpts | None = None):
        """Log a message with a specified level"""
        if not opts:
            opts = LoggerWriteOpts()
        self._internal_logger.opt(depth=opts.depth, colors=opts.colors, ansi=opts.ansi).log(level.name, message)

    def trace(self, message: str):
        self._internal_logger.opt(depth=1).log(Level.TRACE.name, message)

    def debug(self, message: str):
        self._internal_logger.opt(depth=1).log(Level.DEBUG.name, message)

    def info(self, message: str):
        self._internal_logger.opt(depth=1).log(Level.INFO.name, message)

    def warning(self, message: str):
        self._internal_logger.opt(depth=1).log(Level.WARNING.name, message)

    def warn(self, message: str):
        self._internal_logger.opt(depth=1).log(Level.WARNING.name, message)

    def error(self, message: str):
        self._internal_logger.opt(depth=1).log(Level.ERROR.name, message)

    def critical(self, message: str):
        self._internal_logger.opt(depth=1).log(Level.CRITICAL.name, message)


class StreamRedirector(IO):
    def __init__(self, logger: Logger, level: Level = Level.INFO):
        self._level = level
        self._logger = logger

    def write(self, buffer):
        for line in buffer.rstrip().splitlines():
            self._logger.log(self._level, line.rstrip(), LoggerWriteOpts(depth=2))

    def flush(self):
        pass
