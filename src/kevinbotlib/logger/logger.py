import contextlib
import glob
import os
import sys
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from io import TextIOBase
from typing import IO

import loguru._logger
import platformdirs
from deprecated import deprecated
from loguru import logger as _internal_logger
from loguru._handler import Message

from kevinbotlib.exceptions import LoggerNotConfiguredException


class LoggerDirectories:
    @staticmethod
    def get_logger_directory(*, ensure_exists: bool = True) -> str:
        """
        Returns the log directory path and ensures its existence if needed.

        Args:
            ensure_exists: Create the directory if it doesn't exist.

        Returns:
            The log directory path.
        """
        log_dir = platformdirs.user_data_dir("kevinbotlib/logging", ensure_exists=ensure_exists)
        os.makedirs(log_dir, exist_ok=True)
        return log_dir

    @staticmethod
    def cleanup_logs(directory: str, max_size_mb: int = 500) -> None:
        """
        Deletes oldest log files if the total log directory exceeds max_size_mb.

        Args:
            directory: Log directory path.
            max_size_mb: Maximum size of the log directory in MB.
        """

        log_files = sorted(glob.glob(os.path.join(directory, "*.log")), key=os.path.getctime)

        while log_files and LoggerDirectories.get_directory_size(directory) > max_size_mb:
            os.remove(log_files.pop(0))  # Delete oldest file

    @staticmethod
    def get_directory_size(directory: str) -> float:
        """
        Returns the size of the directory in MB.

        Args:
            directory: Directory to measure size.

        Returns:
            Directory size in MB.
        """

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
    """Options for writing to the logger"""

    depth: int = 1
    """Logger depth. Used to determine the statement that triggered the log. Defaults to 1."""

    colors: bool = True
    """Enable colorized output. Defaults to True."""

    ansi: bool = True
    """Enable ANSI escape codes. Defaults to True."""

    exception: bool | BaseException = False
    """Exception to send to the logger. Defaults to False."""


@dataclass
class FileLoggerConfig:
    """Configuration for file-based logging"""

    directory: str = field(default_factory=LoggerDirectories.get_logger_directory)
    """Directory to store log files. Defaults to the user's data directory."""

    rotation_size: str = "150MB"
    """Rotation size for the log file. Defaults to 150MB."""

    level: Level | None = None
    """Logging level for the log file. Defaults to the global logging level."""


@dataclass
class LoggerConfiguration:
    """Configuration for the logger"""

    level: Level = Level.INFO
    """Global logging level. Defaults to INFO."""

    enable_stderr_logger: bool = True
    """Enable logging to stderr. Defaults to True."""

    file_logger: FileLoggerConfig | None = None
    """File-based logging configuration. Defaults to None."""


class _Sink(TextIOBase):
    def write(self, data):
        # noinspection PyBroadException
        with contextlib.suppress(Exception):
            sys.__stderr__.write(str(data))
        return len(data) if isinstance(data, str) else 0

    def flush(self):
        # noinspection PyBroadException
        with contextlib.suppress(Exception):
            sys.__stderr__.flush()

    def isatty(self):
        # noinspection PyBroadException
        try:
            return sys.__stderr__.isatty
        except Exception:  # noqa: BLE001
            return False


class Logger:
    is_configured = False
    _suppress = False

    def __init__(self) -> None:
        """Create a logger instance"""

        self._internal_logger = _internal_logger
        self._config: LoggerConfiguration | None = None

    @property
    def config(self) -> LoggerConfiguration | None:
        """
        Get the current logger configuration.

        Returns:
            Current global logger configuration.
        """
        return self._config

    @property
    def loguru_logger(self) -> loguru._logger.Logger:
        """
        Get the internal loguru logger instance.

        Returns:
            Loguru logger.
        """

        return self._internal_logger

    @classmethod
    @contextmanager
    def suppress(cls):
        """Content manager to suppress all logging."""

        cls._suppress = True
        try:
            yield
        finally:
            cls._suppress = False

    def configure(self, config: LoggerConfiguration) -> None:
        """
        Configures file-based logging with rotation and cleanup.

        Args:
            config: Logger configuration.
        """

        Logger.is_configured = True
        self._config = config
        self._internal_logger.remove()
        if config.enable_stderr_logger:
            self._internal_logger.add(_Sink(), level=config.level.value.no)  # type: ignore

        if config.file_logger:
            timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]  # Trim to ms
            log_file = os.path.join(config.file_logger.directory, f"{timestamp}.log")

            self._internal_logger.add(
                log_file,
                rotation=config.file_logger.rotation_size,
                format="{message}",
                enqueue=True,
                serialize=True,
                level=config.file_logger.level.value.no if config.file_logger.level else config.level.value.no,
            )
            return log_file
        return None

    def add_hook(self, hook: Callable[[Message], None]) -> None:
        """
        Add a new serialized logger write hook.

        Args:
            hook: Logger write hook.
        """

        if not self.config:
            raise LoggerNotConfiguredException
        self._internal_logger.add(
            hook,  # type: ignore
            level=self.config.level.value.no if self.config.level else self.config.level.value.no,
            serialize=True,
            format="{message}",
            colorize=True,
        )

    def add_hook_ansi(self, hook: Callable[[str], None]) -> None:
        """
        Add a new ANSI logger write hook.

        Args:
            hook: Logger write hook.
        """

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
    ) -> None:
        """
        Log a message with the specified level and options.

        Args:
            level: Logger level
            message: Message to log. Can be a string or an exception.
            opts: Logger options.
        """

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

    def trace(self, message: str) -> None:
        """
        Log a trace message.

        Args:
            message: Message
        """

        if not Logger.is_configured:
            raise LoggerNotConfiguredException

        if Logger._suppress:
            return

        self._internal_logger.opt(depth=1).log(Level.TRACE.name, message)

    def debug(self, message: str) -> None:
        """
        Log a debug message.

        Args:
            message: Message
        """

        if not Logger.is_configured:
            raise LoggerNotConfiguredException

        if Logger._suppress:
            return

        self._internal_logger.opt(depth=1).log(Level.DEBUG.name, message)

    def info(self, message: str) -> None:
        """
        Log an info message.

        Args:
            message: Message
        """

        if not Logger.is_configured:
            raise LoggerNotConfiguredException

        if Logger._suppress:
            return

        self._internal_logger.opt(depth=1).log(Level.INFO.name, message)

    def warning(self, message: str) -> None:
        """
        Log a warning message.

        Args:
            message: Message
        """

        if not Logger.is_configured:
            raise LoggerNotConfiguredException

        if Logger._suppress:
            return

        self._internal_logger.opt(depth=1).log(Level.WARNING.name, message)

    @deprecated("Use Logger.warning() instead")
    def warn(self, message: str) -> None:
        """
        Log a warning message. Deprecated. Use Logger.warning() instead.

        Args:
            message: Message
        """

        self.warning(message)

    def error(self, message: str) -> None:
        """
        Log an error message.

        Args:
            message: Message
        """

        if not Logger.is_configured:
            raise LoggerNotConfiguredException

        if Logger._suppress:
            return

        self._internal_logger.opt(depth=1).log(Level.ERROR.name, message)

    def security(self, message: str) -> None:
        """
        Log a security message.

        Args:
            message: Message
        """

        if not Logger.is_configured:
            raise LoggerNotConfiguredException

        if Logger._suppress:
            return

        self._internal_logger.opt(depth=1).log(Level.SECURITY.name, message)

    def critical(self, message: str) -> None:
        if not Logger.is_configured:
            raise LoggerNotConfiguredException

        if Logger._suppress:
            return

        self._internal_logger.opt(depth=1).log(Level.CRITICAL.name, message)


class StreamRedirector(IO):
    """Redirect a stream to logging"""

    def __init__(self, logger: Logger, level: Level = Level.INFO):
        """
        Initialize the log stream redirector.

        Args:
            logger: Logger to redirect the stream to.
            level: Level to log at.
        """

        self._level = level
        self._logger = logger

    def write(self, buffer):
        for line in buffer.rstrip().splitlines():
            self._logger.log(self._level, line.rstrip(), LoggerWriteOpts(depth=2))

    def flush(self):
        pass
