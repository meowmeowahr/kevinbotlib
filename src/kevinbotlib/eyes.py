# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import atexit
import time
from collections.abc import Callable
from threading import Thread
from typing import Any

from loguru import logger
from serial import Serial

from kevinbotlib.core import KevinbotConnectionType
from kevinbotlib.exceptions import HandshakeTimeoutException
from kevinbotlib.states import EyeSettings, KevinbotEyesState, Skin


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
                serial.write(b"getSettings=true\n")
                serial.write(b"handshake.complete\n")
                break

            if time.monotonic() - start_time > timeout:
                msg = "Handshake timed out"
                raise HandshakeTimeoutException(msg)

            time.sleep(0.1)  # Avoid spamming the connection

        # Data rx thread
        self.rx_thread = Thread(target=self._rx_loop, args=(serial, "="), daemon=True)
        self.rx_thread.name = "KevinbotLib.Eyes.Rx"
        self.rx_thread.start()

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


    @property
    def callback(self) -> Callable[[str, str | None], Any] | None:
        return self._callback

    @callback.setter
    def callback(self, callback: Callable[[str, str | None], Any]) -> None:
        self._callback = callback

    def _setup_serial(self, port: str, baud: int, timeout: float = 1):
        self.serial = Serial(port, baud, timeout=timeout)
        return self.serial

    def _rx_loop(self, serial: Serial, delimeter: str = "="):
        while True:
            try:
                raw: bytes = serial.readline()
            except TypeError:
                # serial has been stopped
                return

            cmd: str = raw.decode("utf-8").split(delimeter, maxsplit=1)[0].strip().replace('\00', '')
            if not cmd:
                continue

            val: str | None = None
            if len(raw.decode("utf-8").split(delimeter)) > 1:
                val = raw.decode("utf-8").split(delimeter, maxsplit=1)[1].strip("\r\n").replace('\00', '')

            if cmd.startswith("eyeSettings."):
                # Remove prefix and split into path and value
                setting = cmd[len("eyeSettings."):]

                path = setting.split(".")

                if not val:
                    logger.error(f"Got eyeSettings command without a value: {cmd} :: {val}")
                    continue

                # Convert the value to appropriate type
                try:
                    # Handle array values [x, y]
                    if val.startswith("[") and val.endswith("]"):
                        value_str = val.strip("[]")
                        value = tuple(int(x.strip()) for x in value_str.split(","))
                    # Handle hex colors
                    elif val.startswith("#"):
                        value = val
                    # Handle quoted strings
                    elif val.startswith('"') and val.endswith('"'):
                        value = val.strip('"')
                    # Handle numbers
                    else:
                        try:
                            value = int(val)
                        except ValueError:
                            value = val
                except Exception as e:
                    raise ValueError(f"Failed to parse value '{value_str}': {e!s}")

                # Create a dict representation of the settings
                settings_dict = self._state.settings.model_dump()

                # Navigate to the correct nested dictionary
                current_dict = settings_dict
                for i, key in enumerate(path[:-1]):
                    if key not in current_dict:
                        raise ValueError(f"Invalid path: {'.'.join(path[:i+1])}")
                    if not isinstance(current_dict[key], dict):
                        raise ValueError(f"Cannot navigate through non-dict value at {'.'.join(path[:i+1])}")
                    current_dict = current_dict[key]

                # Update the value
                if path[-1] not in current_dict:
                    raise ValueError(f"Invalid setting: {'.'.join(path)}")
                current_dict[path[-1]] = value

                # Create new settings instance with updated values
                self._state.settings = EyeSettings.model_validate(settings_dict)
        
            if self.callback:
                self.callback(cmd, val)

    def set_skin(self, skin: Skin):
        """Set the current skin

        Args:
            skin (int): Skin index
        """
        self._state.settings.states.page = skin
        self.send(f"setState={skin.value}")
