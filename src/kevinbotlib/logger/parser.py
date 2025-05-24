import datetime
from dataclasses import dataclass

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


class LogParser:
    @staticmethod
    def parse(data: str) -> list[LogEntry]:
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
        return entries
