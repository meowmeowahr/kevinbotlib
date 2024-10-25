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


def bringup(config_path: str | Path | None, core_port: str, core_baud: int, xbee_port: str, xbee_api: int, xbee_baud: int, *, verbose: bool, trace: bool):
    config = KevinbotConfig(ConfigLocation.MANUAL, config_path) if config_path else KevinbotConfig(ConfigLocation.AUTO)

    logger.info(f"Loaded config at {config.config_path}")
