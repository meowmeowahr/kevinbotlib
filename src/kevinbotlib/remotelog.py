import contextlib
from collections.abc import Callable
from typing import Any

from kevinbotlib.comm import CommPath, CommunicationClient, StringSendable
from kevinbotlib.exceptions import LoggerNotConfiguredException
from kevinbotlib.logger import Logger


class ANSILogSender:
    def __init__(self, logger: Logger, client: "CommunicationClient", key: "CommPath | str"):
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
        with contextlib.suppress(Exception):
            self.client.send(self.key, StringSendable(value=message))


class ANSILogReceiver:
    def __init__(self, callback: Callable[[str], Any], client: "CommunicationClient", key: "CommPath | str"):
        self.callback = callback
        self.client = client
        self.key = key
        self._is_started = False

    def start(self) -> None:
        if self._is_started:
            return
        self.client.add_hook(
            self.key, StringSendable, lambda _, sendable: self.callback(sendable.value) if sendable else None
        )
        self._is_started = True
