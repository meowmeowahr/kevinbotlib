import datetime
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Self

import orjson


@dataclass
class LogEntry:
    """Class representing a single log entry."""

    timestamp: datetime.datetime
    """Timestamp of the log entry."""

    modname: str
    """Module name of the log entry."""

    function: str
    """Function name of the log entry."""

    line: int
    """Line of code where the log entry was generated."""

    level_no: int
    """Log level number."""

    level_name: str
    """Log level name."""

    level_icon: str
    """Log level icon."""

    message: str
    """Messages logged."""


class Log(list):
    """Class representing a list of LogEntry instances."""

    def __init__(self, entries: list[LogEntry] | None = None):
        """
        Create a new log object.

        Args:
            entries: List of LogEntry instances. Defaults to None.
        """

        if entries is None:
            entries = []
        elif isinstance(entries, Log):
            entries = list(entries)
        elif isinstance(entries, list):
            if not all(isinstance(entry, LogEntry) for entry in entries):
                msg = "All entries must be LogEntry instances"
                raise TypeError(msg)
        else:
            msg = f"Expected list[LogEntry], Log, or None, got {type(entries).__name__}"
            raise TypeError(msg)

        super().__init__(entries)

    def append(self, item: LogEntry) -> None:
        """
        Append a new LogEntry to the log.

        Args:
            item: New LogEntry to append.
        """

        if not isinstance(item, LogEntry):
            msg = f"Expected LogEntry, got {type(item).__name__}"
            raise TypeError(msg)
        super().append(item)

    def extend(self, items: "list[LogEntry] | Log") -> None:
        """
        Extend the log with a list of LogEntry instances.

        Args:
            items: List is of LogEntry instances.
        """

        if isinstance(items, Log):
            items = list(items)
        if not isinstance(items, list):
            msg = f"Expected list[LogEntry] or Log, got {type(items).__name__}"
            raise TypeError(msg)
        if not all(isinstance(item, LogEntry) for item in items):
            msg = "All items must be LogEntry instances"
            raise TypeError(msg)
        super().extend(items)

    def insert(self, index: int, item: LogEntry) -> None:
        """
        Insert a new LogEntry into the log at the specified index.

        Args:
            index: Index to insert the LogEntry at.
            item: LogEntry to insert.
        """

        if not isinstance(item, LogEntry):
            msg = f"Expected LogEntry, got {type(item).__name__}"
            raise TypeError(msg)
        super().insert(index, item)

    def __setitem__(self, index: int, item: LogEntry) -> None:
        if not isinstance(item, LogEntry):
            msg = f"Expected LogEntry, got {type(item).__name__}"
            raise TypeError(msg)
        super().__setitem__(index, item)

    def __iadd__(self, items: "list[LogEntry] | Log") -> Self:
        if isinstance(items, Log):
            items = list(items)
        if not isinstance(items, list):
            msg = f"Expected list[LogEntry] or Log, got {type(items).__name__}"
            raise TypeError(msg)
        if not all(isinstance(item, LogEntry) for item in items):
            msg = "All items must be LogEntry instances"
            raise TypeError(msg)
        super().__iadd__(items)
        return self

    def __iter__(self) -> Iterator[LogEntry]:
        return super().__iter__()

    def convert(self):
        raise NotImplementedError


class LogParser:
    """Class for parsing log data."""

    @staticmethod
    def parse(data: str) -> Log:
        """
        Parse raw log file data into a Log object.

        Args:
            data: Log file data.

        Returns: Log object.
        """

        entries = []
        for raw_entry in data.splitlines():
            if not raw_entry:
                continue
            entry = orjson.loads(raw_entry)
            record = entry.get("record", {})

            time = record.get("time", {})
            timestamp = time.get("timestamp", 0.0)

            modname = record.get("name", "")
            function = record.get("function", "")
            line = record.get("line", 0)

            level = record.get("level", {})
            level_name = level.get("name", "")
            level_no = level.get("no", 0)
            level_icon = level.get("icon", "")

            message = entry.get("text", "")

            entries.append(
                LogEntry(
                    datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc),
                    modname,
                    function,
                    line,
                    level_no,
                    level_name,
                    level_icon,
                    message,
                )
            )
        return Log(entries)
