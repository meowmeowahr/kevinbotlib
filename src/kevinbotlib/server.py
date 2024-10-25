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


def bringup(
    config_path: str | Path | None,
    core_port: str | None,
    core_baud: int | None,
    xbee_port: str | None,
    xbee_api: int | None,
    xbee_baud: int | None,
):
    config = KevinbotConfig(ConfigLocation.MANUAL, config_path) if config_path else KevinbotConfig(ConfigLocation.AUTO)
    logger.info(f"Loaded config at {config.config_path}")

    if not core_port:
        core_port = config.core.port
    if not core_baud:
        core_baud = config.core.baud
    if not xbee_port:
        xbee_port = config.xbee.port
    if not xbee_baud:
        xbee_baud = config.xbee.baud
    if not xbee_api:
        xbee_api = config.xbee.api

    robot = Kevinbot()
    robot.connect(core_port, core_baud, config.core.handshake_timeout, config.core.tick, config.core.timeout)
    logger.info(f"New core connection: {core_port}@{core_baud}")
    logger.debug(f"Robot status is: {robot.get_state()}")

    _ = WirelessRadio(robot, xbee_port, xbee_baud, xbee_api, config.xbee.timeout)
    logger.info(f"Xbee connection: {xbee_port}@{xbee_baud}")
