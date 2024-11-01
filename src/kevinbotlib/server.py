# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
KevinbotLib Robot Server
Allow accessing KevinbotLib APIs over MQTT and XBee API Mode
"""

import atexit
import sys
from pathlib import Path

import shortuuid
from loguru import logger
from paho.mqtt.client import CallbackAPIVersion, Client, MQTTMessage  # type: ignore

from kevinbotlib.config import ConfigLocation, KevinbotConfig
from kevinbotlib.core import Drivebase, SerialKevinbot
from kevinbotlib.states import KevinbotServerState
from kevinbotlib.xbee import WirelessRadio


class KevinbotServer:
    def __init__(
        self, config: KevinbotConfig, robot: SerialKevinbot, radio: WirelessRadio, root_topic: str | None
    ) -> None:
        self.config = config
        self.robot = robot
        self.radio = radio
        self.root: str = root_topic if root_topic else self.config.server.root_topic
        self.state: KevinbotServerState = KevinbotServerState()

        self.robot.request_disable()
        self.drive = Drivebase(robot)

        self.radio.callback = self.radio_callback

        logger.info(f"Connecting to MQTT borker at: mqtt://{self.config.mqtt.host}:{self.config.mqtt.port}")
        logger.info(f"Using MQTT root topic: {self.root}")

        # Create mqtt client
        self.client_id = f"kevinbot-server-{shortuuid.random()}"
        self.client = Client(CallbackAPIVersion.VERSION2, client_id=self.client_id)
        self.robot.callback = self.on_robot_state_change
        self.client.on_connect = self.on_mqtt_connect
        self.client.on_message = self.on_mqtt_message
        self.clients = 0
        self.connected_cids: list[str] = []
        self.last_driver_cid: str | None = None

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

    def on_mqtt_connect(self, _, __, ___, rc, props):
        logger.success(f"MQTT client connected: {self.client_id}, rc: {rc}, props: {props}")
        self.client.subscribe(self.root + "/main/state_request", 1)
        self.client.subscribe(self.root + "/main/estop", 1)
        self.client.subscribe(self.root + "/clients/connect", 0)
        self.client.subscribe(self.root + "/clients/disconnect", 0)
        self.client.subscribe("$SYS/broker/clients/connected")
        # self.client.publish(self.root + "/kevinbot/tryenable/st", "False", 1)

    def on_mqtt_message(self, _, __, msg: MQTTMessage):
        logger.trace(f"Got MQTT message at: {msg.topic} payload={msg.payload!r} with qos={msg.qos}")

        if msg.topic.startswith("$SYS"):
            # system data
            match msg.topic:
                case "$SYS/broker/clients/connected":
                    self.clients = int(msg.payload.decode("utf-8")) - 1
                    logger.info(f"There are now {self.clients} connected clients")
            return

        if msg.topic[0] == "/" or msg.topic[-1] == "/":
            logger.warning(f"MQTT topic: {msg.topic} has a leading/trailing slash. Removing it.")
            topic = msg.topic.strip("/")
        else:
            topic = msg.topic

        subtopics = topic.split("/")[1:]
        value = msg.payload.decode("utf-8")
        match subtopics:
            case ["main", "state_request"]:
                if value == "enable":
                    self.robot.request_enable()
                else:
                    self.robot.request_disable()
            case ["clients", "connect"]:
                self.connected_cids.append(value)
                self.client.publish(f"{self.root}/clients/connect/ack", f"ack:{value}")
                logger.info(f"Client connected with cid:{value}")
            case ["clients", "disconnect"]:
                if value in self.connected_cids:
                    self.connected_cids.remove(value)
                self.client.publish(f"{self.root}/clients/disconnect/ack", f"ack:{value}")
                logger.info(f"Client disconnected with cid:{value}")
            case ["main", "estop"]:
                self.robot.e_stop()
            # case ["drive", "power"]:
            #     self.drive.drive_at_power(float(value.split(",", 2)[0])/100, float(value.split(",", 2)[1])/100)

    def on_robot_state_change(self, _: str, __: str | None):
        self.client.publish(f"{self.root}/state", self.robot.get_state().model_dump_json())

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

    robot = SerialKevinbot()
    robot.auto_disconnect = False
    robot.connect(
        config.core.port, config.core.baud, config.core.handshake_timeout, config.core.tick, config.core.timeout
    )
    logger.info(f"New core connection: {config.core.port}@{config.core.baud}")
    logger.debug(f"Robot status is: {robot.get_state()}")

    radio = WirelessRadio(robot, config.xbee.port, config.xbee.baud, config.xbee.api, config.xbee.timeout)
    logger.info(f"Xbee connection: {config.xbee.port}@{config.xbee.baud}")

    KevinbotServer(config, robot, radio, root_topic)
