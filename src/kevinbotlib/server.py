# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
KevinbotLib Robot Server
Allow accessing KevinbotLib APIs over MQTT and XBee API Mode
"""

import sys
import atexit
from pathlib import Path

import shortuuid
from loguru import logger
from paho.mqtt.client import Client

from kevinbotlib.config import ConfigLocation, KevinbotConfig
from kevinbotlib.core import Kevinbot
from kevinbotlib.states import KevinbotServerState
from kevinbotlib.xbee import WirelessRadio


class KevinbotServer:
    def __init__(self, config: KevinbotConfig, robot: Kevinbot, radio: WirelessRadio, root_topic: str | None) -> None:
        self.config = config
        self.robot = robot
        self.radio = radio
        self.root: str = root_topic if root_topic else self.config.server.root_topic
        self.state: KevinbotServerState = KevinbotServerState()

        self.radio.callback = self.radio_callback

        logger.info(f"Connecting to MQTT borker at: mqtt://{self.config.mqtt.host}:{self.config.mqtt.port}")
        logger.info(f"Using MQTT root topic: {self.root}")

        # Create mqtt client
        self.client_id = f"kevinbot-server-{shortuuid.random()}"
        self.client = Client(client_id=self.client_id)
        self.client.on_connect = self.on_mqtt_connect

        try:
            self.client.connect(self.config.mqtt.host, self.config.mqtt.port, self.config.mqtt.keepalive)
        except ConnectionRefusedError as e:
            logger.critical(f"MQTT client failed to connect: {e!r}")
            sys.exit()

        if self.root[0] == "/" or self.root[-1] == "/":
            logger.warning(f"MQTT topic: {self.root} has a leading/trailing slash. Removing it.")
            self.root = self.root.strip("/")

        self.client.loop_start()

        atexit.register(self.stop)

        # Join threads
        if robot.rx_thread:
            robot.rx_thread.join()

    def on_mqtt_connect(self, _, __, ___, rc):
        logger.success(f"MQTT client connected: {self.client_id}, rc: {rc}")
        self.client.subscribe(self.root + "/#")
    
    def radio_callback(self, rf_data: dict):
        logger.trace(f"Got rf packet: {rf_data}")

    def stop(self):
        logger.info("Exiting...")
        self.client.disconnect()
        self.robot.disconnect()
        self.radio.disconnect()

def bringup(
    config_path: str | Path | None,
    root_topic: str | None,
):
    config = KevinbotConfig(ConfigLocation.MANUAL, config_path) if config_path else KevinbotConfig(ConfigLocation.AUTO)
    logger.info(f"Loaded config at {config.config_path}")

    robot = Kevinbot()
    robot.auto_disconnect = False
    robot.connect(
        config.core.port, config.core.baud, config.core.handshake_timeout, config.core.tick, config.core.timeout
    )
    logger.info(f"New core connection: {config.core.port}@{config.core.baud}")
    logger.debug(f"Robot status is: {robot.get_state()}")

    radio = WirelessRadio(robot, config.xbee.port, config.xbee.baud, config.xbee.api, config.xbee.timeout)
    logger.info(f"Xbee connection: {config.xbee.port}@{config.xbee.baud}")

    KevinbotServer(config, robot, radio, root_topic)
