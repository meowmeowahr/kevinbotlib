from typing import TYPE_CHECKING

import xbee
from loguru import logger
from serial import Serial

from kevinbotlib.core import BaseKevinbotSubsystem, SerialKevinbot

if TYPE_CHECKING:
    from collections.abc import Callable


class WirelessRadio(BaseKevinbotSubsystem):
    def __init__(self, robot: SerialKevinbot, port: str, baud: int, api: int, timeout: float) -> None:
        """Initialize Kevinbot Wireless Radio (XBee)

        Args:
            robot (Kevinbot): The main robot class
            port (str): Serial port to connect to `/dev/ttyAMA0` for typical Kevinbot hardware
            baud (int): Baud rate for serial interface `921600` for typical Kevinbot configs
            api (int): API mode for xbee interface `2` for typical Kevinbot configs (`0` isn't supported yet)
            timeout (float): Timeout for serial operations
        """
        super().__init__(robot)

        if api not in [1, 2]:
            logger.error(f"XBee API Mode {api} isn't supported. Assuming API escaped (2)")
            api = 2

        self.callback: Callable | None = None

        self.serial = Serial(port, baud, timeout=timeout)
        self.xbee = xbee.XBee(self.serial, callback=self.callback)

    def get(self) -> dict:
        """Get the latest packet (blocking)

        Returns:
            dict: Data packet
        """
        return self.xbee.wait_read_frame()

    def disconnect(self):
        """Disconnect robot radio, and halt processing"""
        self.xbee.halt()
        self.serial.close()
