# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
KevinbotLib Robot Server
Allow accessing KevinbotLib APIs over MQTT and XBee API Mode
"""

from pathlib import Path

from loguru import logger

from kevinbotlib.config import ConfigLocation, KevinbotConfig
from kevinbotlib.core import Kevinbot
from kevinbotlib.xbee import WirelessRadio

class KevinbotServer:
    def __init__(self, config: KevinbotConfig, robot: Kevinbot, radio: WirelessRadio) -> None:
        self.config = config
        self.robot = robot
        self.radio = radio

        self.radio.callback = self.radio_callback

    def radio_callback(self, rf_data: dict):
        logger.trace(f"Got rf packet: {rf_data}")

def bringup(
    config_path: str | Path | None,
):
    config = KevinbotConfig(ConfigLocation.MANUAL, config_path) if config_path else KevinbotConfig(ConfigLocation.AUTO)
    logger.info(f"Loaded config at {config.config_path}")

    robot = Kevinbot()
    robot.connect(
        config.core.port, config.core.baud, config.core.handshake_timeout, config.core.tick, config.core.timeout
    )
    logger.info(f"New core connection: {config.core.port}@{config.core.baud}")
    logger.debug(f"Robot status is: {robot.get_state()}")

    radio = WirelessRadio(robot, config.xbee.port, config.xbee.baud, config.xbee.api, config.xbee.timeout)
    logger.info(f"Xbee connection: {config.xbee.port}@{config.xbee.baud}")

    KevinbotServer(config, robot, radio)
