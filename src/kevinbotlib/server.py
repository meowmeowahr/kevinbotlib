# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
KevinbotLib Robot Server
Allow accessing KevinbotLib APIs over MQTT
"""

import atexit
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Thread

import shortuuid
from loguru import logger
from paho.mqtt.client import CallbackAPIVersion, Client, MQTTMessage  # type: ignore

from kevinbotlib.config import ConfigLocation, KevinbotConfig
from kevinbotlib.core import Drivebase, SerialKevinbot, Servos
from kevinbotlib.eyes import EyeMotion, EyeSkin, SerialEyes
from kevinbotlib.models import KevinbotServerState


class KevinbotServer:
    def __init__(self, config: KevinbotConfig, robot: SerialKevinbot, root_topic: str | None) -> None:
        self.config = config
        self.robot = robot
        self.root: str = root_topic if root_topic else self.config.server.root_topic

        self.state: KevinbotServerState = KevinbotServerState()
        self.state.timestamp = datetime.now(timezone.utc)
        self.state.heartbeat_freq = self.config.server.heartbeat

        self.robot.request_disable()
        self.drive = Drivebase(robot)
        self.servos = Servos(robot)

        if config.server.enable_eyes:
            self.eyes = SerialEyes()
            self.eyes.on_state_updated = self.on_eye_state_change
            self.eyes.connect(
                self.config.eyes.port,
                self.config.eyes.baud,
                self.config.eyes.handshake_timeout,
                self.config.eyes.handshake_timeout,
            )
        else:
            self.eyes = None

        logger.info(f"Connecting to MQTT borker at: mqtt://{self.config.mqtt.host}:{self.config.mqtt.port}")
        logger.info(f"Using MQTT root topic: {self.root}")

        # Create mqtt client
        self.cid = shortuuid.random()
        self.client_id = f"kevinbot-server-{self.cid}"
        self.client = Client(CallbackAPIVersion.VERSION2, client_id=self.client_id)
        self.robot.on_data = self.on_robot_state_change
        self.client.on_connect = self.on_mqtt_connect
        self.client.on_message = self.on_mqtt_message

        try:
            self.client.connect(self.config.mqtt.host, self.config.mqtt.port, self.config.mqtt.keepalive)
        except ConnectionRefusedError as e:
            logger.critical(f"MQTT client failed to connect: {e!r}")
            sys.exit()

        if self.root[0] == "/" or self.root[-1] == "/":
            logger.warning(f"MQTT topic: {self.root} has a leading/trailing slash. Removing it.")
            self.root = self.root.strip("/")

        self.heartbeat_thread = Thread(target=self.heartbeat_loop, daemon=True)
        self.heartbeat_thread.name = f"KevinbotLib.Server.Heartbeat:{self.cid}"
        self.heartbeat_thread.start()

        self.client_hb_thread = Thread(
            target=self.client_hb_loop,
            args=(self.config.server.client_heartbeat + self.config.server.client_heartbeat_tolerance,),
            daemon=True,
        )
        self.client_hb_thread.name = f"KevinbotLib.Server.ClientHeartbeat:{self.cid}"
        self.client_hb_thread.start()

        self.client.loop_start()

        atexit.register(self.stop)

        # timestamp updater
        while True:
            self.state.timestamp = datetime.now(timezone.utc)
            self.on_server_state_change()
            time.sleep(1)

    def client_hb_loop(self, heartbeat: float):
        while True:
            for cid, value in self.state.cid_heartbeats.items():
                if datetime.fromtimestamp(float(value), timezone.utc) < datetime.now(timezone.utc) - timedelta(
                    seconds=heartbeat
                ):
                    # client is dead
                    if cid in self.state.connected_cids:
                        self.state.connected_cids.remove(cid)
                        self.state.dead_cids.append(cid)
                        if cid == self.state.driver_cid:
                            self.drive.stop()
                            self.state.driver_cid = None
                            self.client.publish(f"{self.root}/drive/driver", "NULL", 0)

                elif cid in self.state.dead_cids:
                    self.state.connected_cids.append(cid)
                    self.state.dead_cids.remove(cid)

            time.sleep(heartbeat)

    def heartbeat_loop(self):
        while True:
            self.client.publish(f"{self.root}/server/heartbeat", json.dumps({"uptime": time.process_time()}), 0)
            time.sleep(self.config.server.heartbeat)

    def on_mqtt_connect(self, _, __, ___, rc, props):
        logger.success(f"MQTT client connected: {self.client_id}, rc: {rc}, props: {props}")
        self.client.subscribe(self.root + "/main/state_request", 1)
        self.client.subscribe(self.root + "/main/estop", 1)
        self.client.subscribe(self.root + "/clients/connect", 0)
        self.client.subscribe(self.root + "/clients/disconnect", 0)
        self.client.subscribe(self.root + "/clients/heartbeat", 0)
        self.client.subscribe(self.root + "/drive/power", 1)
        self.client.subscribe(self.root + "/servo/set", 0)
        self.client.subscribe(self.root + "/servo/all", 0)
        self.client.subscribe(self.root + "/eyes/skin", 0)
        self.client.subscribe(self.root + "/eyes/backlight", 0)
        self.client.subscribe(self.root + "/eyes/motion", 0)
        self.client.subscribe(self.root + "/eyes/pos", 0)
        self.client.subscribe(self.root + "/eyes/skinopt", 0)
        self.client.subscribe(self.root + "/eyes/get", 0)
        self.client.subscribe("$SYS/broker/clients/connected")
        self.client.publish(self.root + "/server/startup", datetime.now(timezone.utc).timestamp(), 0)
        self.state.mqtt_connected = True
        self.on_server_state_change()
        self.on_eye_state_change()

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
                    self.state.driver_cid = None
                    self.client.publish(f"{self.root}/drive/driver", "NULL", 0)
                    self.on_server_state_change()
            case ["clients", "connect"]:
                self.state.connected_cids.append(value)
                logger.info(f"Client connected with cid:{value}")
                self.on_server_state_change()
                self.client.publish(f"{self.root}/clients/connect/ack", f"ack:{value}")
            case ["clients", "disconnect"]:
                if value in self.state.connected_cids:
                    self.state.connected_cids.remove(value)
                if self.state.driver_cid == value:
                    self.state.driver_cid = None
                    self.client.publish(f"{self.root}/drive/driver", "NULL", 0)
                if value in self.state.cid_heartbeats:
                    self.state.cid_heartbeats.pop(value)
                self.client.publish(f"{self.root}/clients/disconnect/ack", f"ack:{value}")
                logger.info(f"Client disconnected with cid:{value}")
                self.on_server_state_change()
            case ["clients", "heartbeat"]:
                values = value.split(":", 2)
                if len(values) != 2:  # noqa: PLR2004
                    return
                self.state.cid_heartbeats[values[0]] = float(values[1])
            case ["main", "estop"]:
                self.robot.e_stop()
                self.state.driver_cid = None
                self.client.publish(f"{self.root}/drive/driver", "NULL", 0)
            case ["drive", "power"]:
                values = value.strip().split(",")

                # check command format
                if len(values) != 4:  # Expecting "left,right,cid,timestamp" # noqa: PLR2004
                    logger.error(f"Invalid drive power format. Expected 'left,right,cid,timestamp', got: {value!r}")
                    return

                # check drive powers
                if not all(v.replace(".", "", 1).replace("-", "", 1).isdigit() for v in values[:2]):
                    logger.error(f"Drive powers must be numbers, got: {value!r}")
                    return

                # check timestamp format
                cid, timestamp_str = values[2], values[3]
                try:
                    command_time = datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)
                except ValueError:
                    logger.error(f"Invalid timestamp format: {timestamp_str}")
                    return

                # check timestamp
                if self.state.timestamp and (
                    abs(self.state.timestamp - command_time) > timedelta(seconds=self.config.server.drive_ts_tolerance)
                ):
                    logger.warning(
                        f"Drive command timestamp out of sync: {command_time}, current time: {self.state.timestamp}"
                    )
                    self.client.publish(f"{self.root}/drive/warning", "Timestamp out of sync", 0)
                    return

                # Update state with new timestamp
                self.state.last_drive_command_time = self.state.timestamp

                # Process the drive command
                left = float(values[0]) / 100
                right = float(values[1]) / 100

                if cid not in self.state.connected_cids:
                    logger.error(f"Unknown cid {cid} is trying to drive. Request denied")
                    return

                if cid not in self.state.cid_heartbeats:
                    logger.error(f"CID {cid} is not publishing a heartbeat. Drive request denied.")
                    return

                if self.state.driver_cid != cid and self.state.driver_cid is not None:
                    logger.error(f"CID {self.state.driver_cid} is already driving, {cid} request denied")
                    return

                if cid in self.state.dead_cids:
                    logger.error(f"A dead CID, {cid} is trying to drive. Request denied")
                    return

                # state updates
                self.state.driver_cid = None if (left == 0 and right == 0) else cid
                self.client.publish(f"{self.root}/drive/driver", self.state.driver_cid, 0)
                self.client.publish(f"{self.root}/drive/last_driver", cid, 0)
                self.on_server_state_change()

                # check drive power range
                if not (-1 <= left <= 1 and -1 <= right <= 1):
                    logger.error(
                        f"Drive powers must be between -100 and 100: left={left*100:.1f}, right={right*100:.1f}"
                    )
                    return

                # drive
                self.drive.drive_at_power(left, right)
            case ["servo", "set"]:
                values = value.strip().split(",")
                if len(values) != 2:  # noqa: PLR2004
                    logger.error(f"Invalid servo data format. Expected 'channel,degrees', got: {value!r}")
                    return

                if not all(v.isdigit() for v in values):
                    logger.error(f"Servo values must be numbers, got: {value!r}")
                    return

                ch = int(values[0])
                deg = int(values[1])

                if not (0 <= ch <= len(self.servos)):
                    logger.error(f"Servo channel must be 0~{len(self.servos)}")
                    return

                self.servos[ch].angle = deg
            case ["servo", "all"]:
                if not value.isdigit():
                    logger.error(f"Servo value must be numbers, got: {value!r}")
                    return

                self.servos.all = int(value)
            case ["eyes", "skin"]:
                if not value.isdigit():
                    logger.error(f"Eye skin value must be numbers, got: {value!r}")
                    return

                if self.eyes:
                    self.eyes.set_skin(EyeSkin(int(value)))
                else:
                    logger.warning(f"Attempted to set eye skin value, {subtopics}, eyes are disabled")
                self.on_eye_state_change()
            case ["eyes", "motion"]:
                if not value.isdigit():
                    logger.error(f"Eye skin value must be numbers, got: {value!r}")
                    return

                if self.eyes:
                    self.eyes.set_motion(EyeMotion(int(value)))
                else:
                    logger.warning(f"Attempted to set eye motion value, {subtopics}, eyes are disabled")
                self.on_eye_state_change()
            case ["eyes", "backlight"]:
                if not value.isdigit():
                    logger.error(f"Eye backlight value must be numbers, got: {value!r}")
                    return

                if self.eyes:
                    self.eyes.set_backlight(max(0, min(1, int(value) / 255)))
                else:
                    logger.warning(f"Attempted to set eye backlight value, {subtopics}, eyes are disabled")
                self.on_eye_state_change()
            case ["eyes", "pos"]:
                values = value.strip().split(",")
                if len(values) != 2:  # noqa: PLR2004
                    logger.error(f"Invalid eye position format. Expected 'x,y', got: {value!r}")
                    return

                if not all(v.isdigit() for v in values):
                    logger.error(f"Eye position values must be numbers, got: {value!r}")
                    return

                x = int(values[0])
                y = int(values[1])

                if not (0 <= x <= self.config.eyes.resolution_x):
                    logger.error(
                        f"X must be 0~{self.config.eyes.resolution_x}, if your screen is larger, use the `kevinbot config set eyes.resolution_x <NEW_VALUE> --int`"
                    )
                    return
                if not (0 <= y <= self.config.eyes.resolution_y):
                    logger.error(
                        f"X must be 0~{self.config.eyes.resolution_y}, if your screen is larger, use the `kevinbot config set eyes.resolution_y <NEW_VALUE> --int`"
                    )
                    return

                if self.eyes:
                    self.eyes.set_manual_pos(x, y)
                else:
                    logger.warning(f"Attempted to set eye pos value, {subtopics}, eyes are disabled")
                self.on_eye_state_change()
            case ["eyes", "skinopt"]:
                values = value.strip().split(":")
                if len(values) < 3:  # noqa: PLR2004
                    logger.error(
                        f"Invalid eye position format. Expected 'skin:arg0:[...]:value' or 'skin:arg0:value', got: {value!r}"
                    )
                    return

                if self.eyes:
                    self.eyes.set_skin_option(values)
                else:
                    logger.warning(f"Attempted to set eye skinopt value, {subtopics}, eyes are disabled")
            case ["eyes", "get"]:
                if self.eyes:
                    self.eyes.update()
                else:
                    logger.warning(f"Attempted to get eye settings, {subtopics}, eyes are disabled")

    def on_robot_state_change(self, _: str, __: str | None):
        self.client.publish(f"{self.root}/state", self.robot.get_state().model_dump_json())

    def on_server_state_change(self):
        self.client.publish(f"{self.root}/serverstate", self.state.model_dump_json())

    def on_eye_state_change(self, *_):
        if self.eyes:
            self.client.publish(f"{self.root}/eyes/state", self.eyes.get_state().model_dump_json())

    def radio_callback(self, rf_data: dict):
        logger.trace(f"Got rf packet: {rf_data}")

    def stop(self):
        logger.info("Exiting...")
        self.client.publish(f"{self.root}/server/shutdown", datetime.now(timezone.utc).timestamp(), 0).wait_for_publish(
            1
        )
        self.client.disconnect()
        self.robot.disconnect()


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

    KevinbotServer(config, robot, root_topic)


if __name__ == "__main__":
    bringup(None, None)
