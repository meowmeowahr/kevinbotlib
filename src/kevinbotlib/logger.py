import glob
import os
import sys
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import IO

import platformdirs
from deprecated import deprecated
from loguru import logger as _internal_logger
from loguru._handler import Message

from kevinbotlib.exceptions import LoggerNotConfiguredException


class LoggerDirectories:
    @staticmethod
    def get_logger_directory(*, ensure_exists=True) -> str:
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
    """Logging levels"""

    TRACE = _internal_logger.level("TRACE")
    "Trace level logging - used for more detailed info than DEBUG - level no. 5"

    DEBUG = _internal_logger.level("DEBUG")
    "Debug level logging - used for debugging info - level no. 10"

    INFO = _internal_logger.level("INFO")
    "Debug level logging - used for regular info - level no. 20"

    WARNING = _internal_logger.level("WARNING")
    "Warnng level logging - used for warnings and recommended fixes - level no. 30"

    ERROR = _internal_logger.level("ERROR")
    "Error level logging - used for non-critical and recoverable errors - level no. 40"

    SECURITY = _internal_logger.level("SECURITY", 45, "<bg 202><bold>")
    "Security level logging - used for non-application-breaking secutiry issues/threats - level no. 45"

    CRITICAL = _internal_logger.level("CRITICAL")
    "Error level logging - used for critical and non-recoverable errors - level no. 50"


@dataclass
class LoggerWriteOpts:
    depth: int = 1
    colors: bool = True
    ansi: bool = True
    exception: bool | BaseException = False


@dataclass
class FileLoggerConfig:
    directory: str = field(default_factory=LoggerDirectories.get_logger_directory)
    rotation_size: str = "150MB"
    level: Level | None = None


@dataclass
class LoggerConfiguration:
    level: Level = Level.INFO
    file_logger: FileLoggerConfig | None = None


class Logger:
    is_configured = False
    _suppress = False

    def __init__(self) -> None:
        self._internal_logger = _internal_logger
        self._config: LoggerConfiguration | None = None

    @property
    def config(self) -> LoggerConfiguration | None:
        return self._config

    @property
    def loguru_logger(self):
        return self._internal_logger

    @classmethod
    @contextmanager
    def suppress(cls):
        cls._suppress = True
        try:
            yield
        finally:
            cls._suppress = False

    def configure(self, config: LoggerConfiguration):
        """Configures file-based logging with rotation and cleanup."""
        Logger.is_configured = True
        self._config = config
        self._internal_logger.remove()
        self._internal_logger.add(sys.stderr, level=config.level.value.no)

        if config.file_logger:
            timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]  # Trim to ms
            log_file = os.path.join(config.file_logger.directory, f"{timestamp}.log")

            self._internal_logger.add(
                log_file,
                rotation=config.file_logger.rotation_size,
                enqueue=True,
                serialize=True,
                level=config.file_logger.level.value.no if config.file_logger.level else config.level.value.no,
            )
            return log_file
        return None

    def add_hook(self, hook: Callable[[Message], None]):
        if not self.config:
            raise LoggerNotConfiguredException
        self._internal_logger.add(
            hook,  # type: ignore
            level=self.config.level.value.no if self.config.level else self.config.level.value.no,
            serialize=True,
            colorize=True,
        )

    def add_hook_ansi(self, hook: Callable[[str], None]):
        if not self.config:
            raise LoggerNotConfiguredException
        self._internal_logger.add(
            hook,
            level=self.config.level.value.no if self.config.level else self.config.level.value.no,
            serialize=False,
            colorize=True,
        )

    def log(
        self,
        level: Level,
        message: str | BaseException,
        opts: LoggerWriteOpts | None = None,
    ):
        """Log a message with a specified level"""
        if not Logger.is_configured:
            raise LoggerNotConfiguredException

        if Logger._suppress:
            return

        opts = opts or LoggerWriteOpts()
        self._internal_logger.opt(
            depth=opts.depth,
            colors=opts.colors,
            ansi=opts.ansi,
            exception=opts.exception,
        ).log(level.name, message)

    def trace(self, message: str):
        if not Logger.is_configured:
            raise LoggerNotConfiguredException

        if Logger._suppress:
            return

        self._internal_logger.opt(depth=1).log(Level.TRACE.name, message)

    def debug(self, message: str):
        if not Logger.is_configured:
            raise LoggerNotConfiguredException

        if Logger._suppress:
            return

        self._internal_logger.opt(depth=1).log(Level.DEBUG.name, message)

    def info(self, message: str):
        if not Logger.is_configured:
            raise LoggerNotConfiguredException

        if Logger._suppress:
            return

        self._internal_logger.opt(depth=1).log(Level.INFO.name, message)

    def warning(self, message: str):
        if not Logger.is_configured:
            raise LoggerNotConfiguredException

        if Logger._suppress:
            return

        self._internal_logger.opt(depth=1).log(Level.WARNING.name, message)

    @deprecated("Use Logger.warning() instead")
    def warn(self, message: str):
        self.warning(message)

    def error(self, message: str):
        if not Logger.is_configured:
            raise LoggerNotConfiguredException

        if Logger._suppress:
            return

        self._internal_logger.opt(depth=1).log(Level.ERROR.name, message)

    def security(self, message: str):
        if not Logger.is_configured:
            raise LoggerNotConfiguredException

        if Logger._suppress:
            return

        self._internal_logger.opt(depth=1).log(Level.SECURITY.name, message)

    def critical(self, message: str):
        if not Logger.is_configured:
            raise LoggerNotConfiguredException

        if Logger._suppress:
            return

        self._internal_logger.opt(depth=1).log(Level.CRITICAL.name, message)


class StreamRedirector(IO):
    """Redirect a stream to logging"""

    def __init__(self, logger: Logger, level: Level = Level.INFO):
        self._level = level
        self._logger = logger

    def write(self, buffer):
        for line in buffer.rstrip().splitlines():
            self._logger.log(self._level, line.rstrip(), LoggerWriteOpts(depth=2))

    def flush(self):
        pass
