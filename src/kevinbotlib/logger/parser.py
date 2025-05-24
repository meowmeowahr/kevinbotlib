import datetime
from dataclasses import dataclass
from typing import Self, Iterator

import orjson


@dataclass
class LogEntry:
    timestamp: datetime.datetime
    modname: str
    function: str
    line: int
    level_no: int
    level_name: str
    level_icon: str
    message: str


class Log(list):
    def __init__(self, entries: list[LogEntry] | None = None):
        if entries is None:
            entries = []
        elif isinstance(entries, Log):
            entries = list(entries)
        elif isinstance(entries, list):
            if not all(isinstance(entry, LogEntry) for entry in entries):
                raise TypeError("All entries must be LogEntry instances")
        else:
            raise TypeError(f"Expected list[LogEntry], Log, or None, got {type(entries).__name__}")

        super().__init__(entries)

    def append(self, item: LogEntry) -> None:
        if not isinstance(item, LogEntry):
            raise TypeError(f"Expected LogEntry, got {type(item).__name__}")
        super().append(item)

    def extend(self, items: 'list[LogEntry] | Log') -> None:
        if isinstance(items, Log):
            items = list(items)
        if not isinstance(items, list):
            raise TypeError(f"Expected list[LogEntry] or Log, got {type(items).__name__}")
        if not all(isinstance(item, LogEntry) for item in items):
            raise TypeError("All items must be LogEntry instances")
        super().extend(items)

    def insert(self, index: int, item: LogEntry) -> None:
        if not isinstance(item, LogEntry):
            raise TypeError(f"Expected LogEntry, got {type(item).__name__}")
        super().insert(index, item)

    def __setitem__(self, index: int, item: LogEntry) -> None:
        if not isinstance(item, LogEntry):
            raise TypeError(f"Expected LogEntry, got {type(item).__name__}")
        super().__setitem__(index, item)

    def __iadd__(self, items: 'list[LogEntry] | Log') -> Self:
        if isinstance(items, Log):
            items = list(items)
        if not isinstance(items, list):
            raise TypeError(f"Expected list[LogEntry] or Log, got {type(items).__name__}")
        if not all(isinstance(item, LogEntry) for item in items):
            raise TypeError("All items must be LogEntry instances")
        super().__iadd__(items)
        return self

    def __iter__(self) -> Iterator[LogEntry]:
        return super().__iter__()

    def convert(self):
        raise NotImplementedError


class LogParser:
    @staticmethod
    def parse(data: str) -> Log:
        entries = []
        for entry in data.splitlines():
            if not entry:
                continue
            record = orjson.loads(entry).get("record", {})

            time = record.get("time", {})
            timestamp = time.get("timestamp", 0.0)

            modname = record.get("name", "")
            function = record.get("function", "")
            line = record.get("line", 0)

            level = record.get("level", {})
            level_name = level.get("name", "")
            level_no = level.get("no", 0)
            level_icon = level.get("icon", "")

            message = record.get("message", "")

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
