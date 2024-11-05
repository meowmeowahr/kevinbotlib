# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import atexit
import json
import re
import time
from collections.abc import Callable
from enum import Enum
from threading import Thread
from typing import Any

import shortuuid
from loguru import logger
from paho.mqtt.client import CallbackAPIVersion, Client, MQTTErrorCode, MQTTMessage  # type: ignore
from serial import Serial

from kevinbotlib.core import KevinbotConnectionType
from kevinbotlib.exceptions import HandshakeTimeoutException
from kevinbotlib.states import KevinbotEyesState


class BaseKevinbotEyes:
    """The base Kevinbot Eyes class.

    Not to be used directly
    """

    def __init__(self) -> None:
        self._state = KevinbotEyesState()
        self.type = KevinbotConnectionType.BASE

        self._auto_disconnect = True

    def get_state(self) -> KevinbotEyesState:
        """Gets the current state of the eyes

        Returns:
            KevinbotEyesState: State class
        """
        return self._state

    def disconnect(self):
        """Basic disconnect"""
        self._state.connected = False

    @property
    def auto_disconnect(self) -> bool:
        """Getter for auto disconnect state.

        Returns:
            bool: Whether to disconnect on application exit
        """
        return self._auto_disconnect

    @auto_disconnect.setter
    def auto_disconnect(self, value: bool):
        """Setter for auto disconnect.

        Args:
            value (bool): Whether to disconnect on application exit
        """
        self._auto_disconnect = value
        if value:
            atexit.register(self.disconnect)
        else:
            atexit.unregister(self.disconnect)

    def send(self, data: str):
        """Null implementation of the send method

        Args:
            data (str): Data to send nowhere

        Raises:
            NotImplementedError: Always raised
        """
        msg = f"Function not implemented, attempting to send {data}"
        raise NotImplementedError(msg)


class SerialEyes(BaseKevinbotEyes):
    """The main serial Kevinbot Eyes class"""

    def __init__(self) -> None:
        super().__init__()
        self.type = KevinbotConnectionType.SERIAL

        self.serial: Serial | None = None
        self.rx_thread: Thread | None = None

        self._callback: Callable[[str, str | None], Any] | None = None

        atexit.register(self.disconnect)

    def connect(
        self,
        port: str,
        baud: int,
        timeout: float,
        ser_timeout: float = 0.5,
    ):
        """Start a connection with Kevinbot Eyes

        Args:
            port (str): Serial port to use (`/dev/ttyUSB0` is standard with the typical Kevinbot Hardware)
            baud (int): Baud rate to use (`115200` is typical for the defualt eye configs)
            timeout (float): Timeout for handshake
            ser_timeout (float, optional): Readline timeout, should be lower than `timeout`. Defaults to 0.5.

        Raises:
            HandshakeTimeoutException: Eyes didn't respond to the connection handshake before the timeout
        """
        serial = self._setup_serial(port, baud, ser_timeout)

        start_time = time.monotonic()
        while True:
            serial.write(b"connectionReady\n")

            line = serial.readline().decode("utf-8", errors="ignore").strip("\n")

            if line == "handshake.request":
                serial.write(b"handshake.complete\n")
                break

            if time.monotonic() - start_time > timeout:
                msg = "Handshake timed out"
                raise HandshakeTimeoutException(msg)

            time.sleep(0.1)  # Avoid spamming the connection

        # Data rx thread
        # self.rx_thread = Thread(target=self._rx_loop, args=(serial, "="), daemon=True)
        # self.rx_thread.name = "KevinbotLib.Rx"
        # self.rx_thread.start()

        self._state.connected = True

    def disconnect(self):
        super().disconnect()
        if self.serial and self.serial.is_open:
            self.send("resetConnection")
            self.serial.flush()
            self.serial.close()
        else:
            logger.warning("Already disconnected")

    def send(self, data: str):
        """Send a string through serial.

        Automatically adds a newline.

        Args:
            data (str): Data to send
        """
        self.raw_tx((data + "\n").encode("utf-8"))

    def raw_tx(self, data: bytes):
        """Send raw bytes over serial.

        Args:
            data (bytes): Raw data
        """
        if self.serial:
            self.serial.write(data)
        else:
            logger.warning(f"Couldn't transmit data: {data!r}, Eyes aren't connected")

    def _setup_serial(self, port: str, baud: int, timeout: float = 1):
        self.serial = Serial(port, baud, timeout=timeout)
        return self.serial