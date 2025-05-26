import contextlib
from collections.abc import Callable
from typing import Any

from kevinbotlib.comm import CommPath, RedisCommClient, StringSendable
from kevinbotlib.exceptions import LoggerNotConfiguredException
from kevinbotlib.logger import Logger


class ANSILogSender:
    """Class to send ANSI-formatted log entries over Redis Pub/Sub"""

    def __init__(self, logger: Logger, client: "RedisCommClient", key: "CommPath | str"):
        if not logger.is_configured:
            msg = "Logger must be configured before creating LogSender"
            raise LoggerNotConfiguredException(msg)
        self.logger = logger
        self.client = client
        self.key = key
        self._is_started = False

    def start(self) -> None:
        if self._is_started:
            return
        self.logger.add_hook_ansi(self.hook)
        self._is_started = True

    def hook(self, message):
        with contextlib.suppress(Exception) and Logger.suppress():
            self.client.publish(self.key, StringSendable(value=message))


class ANSILogReceiver:
    """Class to receive ANSI-formatted log entries over Redis Pub/Sub"""

    def __init__(self, callback: Callable[[str], Any], client: "RedisCommClient", key: "CommPath | str"):
        self.callback = callback
        self.client = client
        self.key = key
        self._is_started = False

    def start(self) -> None:
        self.client.subscribe(
            self.key, StringSendable, lambda _, sendable: self.callback(sendable.value) if sendable else None
        )
        self._is_started = True
