from loguru import logger
from serial import Serial
import xbee

from kevinbotlib.core import BaseKevinbotSubsystem, Kevinbot

class WirelessRadio(BaseKevinbotSubsystem):
    def __init__(self, robot: Kevinbot, port: str, baud: int, api: int, timeout: float) -> None:
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

        self.serial = Serial(port, baud, timeout=timeout)
        self.xbee = xbee.XBee(self.serial)