# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import atexit
import json
import re
import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from enum import Enum
from threading import Thread
from typing import TYPE_CHECKING, Any

import shortuuid
from loguru import logger
from paho.mqtt.client import CallbackAPIVersion, Client, MQTTErrorCode, MQTTMessage  # type: ignore
from serial import Serial

from kevinbotlib.exceptions import HandshakeTimeoutException
from kevinbotlib.models import BmsBatteryStatus, KevinbotServerState, KevinbotState, LightingState, MotorDriveStatus

if TYPE_CHECKING:
    from kevinbotlib.eyes import MqttEyes


class KevinbotConnectionType(Enum):
    BASE = 0
    SERIAL = 1
    MQTT = 2


class BaseKevinbotSubsystem:
    """The base subsystem class.

    Not to be used directly
    """

    def __init__(self, robot: "SerialKevinbot | MqttKevinbot") -> None:
        self.robot = robot
        self.robot._register_component(self)  # noqa: SLF001


class BaseKevinbot:
    """The base robot class.

    Not to be used directly
    """

    def __init__(self) -> None:
        self._state = KevinbotState()
        self._server_state = KevinbotServerState()
        self.type = KevinbotConnectionType.BASE
        self._subsystems: list[BaseKevinbotSubsystem] = []

        self._auto_disconnect = True
        self._auto_disable = True

    def get_state(self) -> KevinbotState:
        """Gets the current state of the robot

        Returns:
            KevinbotState: State class
        """
        return self._state

    @property
    def server_state(self) -> KevinbotServerState:
        return self._server_state

    def disconnect(self):
        """Basic robot disconnect"""
        self._state.connected = False
        if self.auto_disable:
            self.request_disable()

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

    @property
    def auto_disable(self) -> bool:
        """Getter for auto disable state.

        Returns:
            bool: Whether to disconnect on application exit
        """
        return self._auto_disable

    @auto_disable.setter
    def auto_disable(self, value: bool):
        """Setter for auto disable.

        Args:
            value (bool): Whether to disconnect on application exit
        """
        self._auto_disable = value

    def send(self, data: str):
        """Null implementation of the send method

        Args:
            data (str): Data to send nowhere

        Raises:
            NotImplementedError: Always raised
        """
        msg = f"Function not implemented, attempting to send {data}"
        raise NotImplementedError(msg)

    def request_enable(self) -> int:
        """Request the core to enable

        Returns:
            int: Always 1
        """
        self.send("kevinbot.tryenable=1")
        return 1

    def request_disable(self) -> int:
        """Request the core to disable

        Returns:
            int: Always 1
        """
        self.send("kevinbot.tryenable=0")
        return 1

    def e_stop(self):
        """Attempt to send and E-Stop signal to the Core"""
        self.send("system.estop")
        self._state.estop = True

    def _register_component(self, component: BaseKevinbotSubsystem):
        self._subsystems.append(component)


class SerialKevinbot(BaseKevinbot):
    """The main serial robot class"""

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
        tick_interval: float,
        ser_timeout: float = 0.5,
        *,
        tick_thread: bool = True,
    ):
        """Start a connection with Kevinbot Core

        Args:
            port (str): Serial port to use (`/dev/ttyAMA2` is standard with the typical Kevinbot Hardware)
            baud (int): Baud rate to use (`921600` is typical for the defualt Core configs)
            timeout (float): Timeout for handshake
            tick_interval (float): How often a heartbeat should be produced
            ser_timeout (float, optional): Readline timeout, should be lower than `timeout`. Defaults to 0.5.
            tick_thread (bool, optional): Whether a tick thread should be started. Defaults to True.

        Raises:
            HandshakeTimeoutException: Core didn't respond to the connection handshake before the timeout
        """
        serial = self._setup_serial(port, baud, ser_timeout)

        start_time = time.monotonic()
        while True:
            serial.write(b"connection.isready=0\n")

            line = serial.readline().decode("utf-8", errors="ignore").strip("\n")

            if line == "ready":
                serial.write(b"connection.start\n")
                serial.write(b"core.errors.clear\n")
                serial.write(b"connection.ok\n")
                break

            if time.monotonic() - start_time > timeout:
                msg = "Handshake timed out"
                raise HandshakeTimeoutException(msg)

            time.sleep(0.1)  # Avoid spamming the connection

        # Data rx thread
        self.rx_thread = Thread(target=self._rx_loop, args=(serial, "="), daemon=True)
        self.rx_thread.name = "KevinbotLib.Rx"
        self.rx_thread.start()

        if tick_thread:
            thread = Thread(target=self.tick_loop, args=(tick_interval,), daemon=True)
            thread.start()
            thread.name = "KevinbotLib.Tick"

        self._state.connected = True

    def disconnect(self):
        """Disconnect core gracefully"""
        super().disconnect()
        if self.serial and self.serial.is_open:
            self.send("core.link.unlink")
            self.serial.flush()
            self.serial.close()
        else:
            logger.warning("Already disconnected")

    @property
    def on_data(self) -> Callable[[str, str | None], Any] | None:
        """Return the data recieved callback function

        Returns:
            Callable[[str, str | None], Any] | None: Callback function
        """
        return self._callback

    @on_data.setter
    def on_data(self, callback: Callable[[str, str | None], Any]) -> None:
        """Set the data recieved callback function

        Args:
            callback (Callable[[str, str  |  None], Any]): Callback function
        """
        self._callback = callback

    def tick_loop(self, interval: float = 1):
        """Send ticks indefinetely

        Args:
            interval (float, optional): Interval between ticks in seconds. Defaults to 1.
        """
        while True:
            self._tick()
            time.sleep(interval)

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
            logger.warning(f"Couldn't transmit data: {data!r}, Core isn't connected")

    def _rx_loop(self, serial: Serial, delimeter: str = "="):
        while True:
            try:
                raw: bytes = serial.readline()
            except TypeError:
                # serial has been stopped
                return

            cmd: str = raw.decode("utf-8").split(delimeter, maxsplit=1)[0].strip()
            if not cmd:
                continue

            val: str | None = None
            if len(raw.decode("utf-8").split(delimeter)) > 1:
                val = raw.decode("utf-8").split(delimeter, maxsplit=1)[1].strip("\r\n")

            match cmd:
                case "ready":
                    pass
                case "core.enabled":
                    if not val:
                        logger.warning("No value recieved for 'core.enabled'")
                        continue
                    if val.lower() in ["true", "t", "1"]:
                        self._state.enabled = True
                    else:
                        self._state.enabled = False
                case "core.uptime":
                    if val:
                        self._state.uptime = int(val)
                case "core.uptime_ms":
                    if val:
                        self._state.uptime_ms = int(val)
                case "connection.requesthandshake":
                    serial.write(b"connection.start\n")
                    serial.write(b"core.errors.clear\n")
                    serial.write(b"connection.ok\n")
                    logger.warning("A handshake was re-requested. This could indicate a core power fault or reset")
                case "motors.amps":
                    if not val:
                        logger.error("No value given for motors.amps")
                        continue

                    try:
                        [int(sv) for sv in val.split(",")]
                    except ValueError:
                        logger.error(f"Values of motion.amps are not ints: {val}")
                        continue

                    self._state.motion.amps = list(map(float, val.split(",")))
                case "motors.watts":
                    if not val:
                        logger.error("No value given for motors.watts")
                        continue

                    try:
                        [int(sv) for sv in val.split(",")]
                    except ValueError:
                        logger.error(f"Values of motion.watts are not ints: {val}")
                        continue

                    self._state.motion.watts = list(map(float, val.split(",")))
                case "motors.status":
                    if not val:
                        logger.error("No value given for motors.status")
                        continue

                    try:
                        [int(sv) for sv in val.split(",")]
                    except ValueError:
                        logger.error(f"Values of motion.status are not ints: {val}")
                        continue

                    self._state.motion.status = [MotorDriveStatus(int(x)) for x in val.split(",")]
                case "bms.voltages":
                    if not val:
                        logger.error("No value given for bms.voltages")
                        continue

                    try:
                        [int(sv) for sv in val.split(",")]
                    except ValueError:
                        logger.error(f"Values of bms.voltages are not ints: {val}")
                        continue

                    self._state.battery.voltages = [float(x) / 10 for x in val.split(",")]
                case "bms.raw_voltages":
                    if val:
                        self._state.battery.raw_voltages = [float(x) / 10 for x in val.split(",")]
                case "bms.status":
                    if val:
                        self._state.battery.states = [BmsBatteryStatus(int(x)) for x in val.split(",")]
                case "sensors.gyro":
                    if not val:
                        logger.error("No value given for sensors.gyro")
                        continue

                    try:
                        [int(sv) for sv in val.split(",")]
                    except ValueError:
                        logger.error(f"Values of sensors.gyro are not ints: {val}")
                        continue

                    self._state.imu.gyro = [int(x) for x in val.split(",")]
                case "sensors.accel":
                    if not val:
                        logger.error("No value given for sensors.accel")
                        continue

                    try:
                        [int(sv) for sv in val.split(",")]
                    except ValueError:
                        logger.error(f"Values of sensors.accel are not ints: {val}")
                        continue

                    self._state.imu.accel = [int(x) for x in val.split(",")]
                case "sensors.temps":
                    if val:
                        temps = val.split(",")
                        valid = True
                        for temp in temps:
                            if not re.match("^[-+]?[0-9]+$", temp):
                                logger.error(f"Found non-integer value in temps, {temps}")
                                valid = False
                                break
                        if valid:
                            self._state.thermal.left_motor = int(temps[0]) / 100
                            self._state.thermal.right_motor = int(temps[1]) / 100
                            self._state.thermal.internal = int(temps[2]) / 100
                case "sensors.bme":
                    if val:
                        vals = val.split(",")
                        for value in vals:
                            if not re.match("^[-+]?[0-9]+$", value):
                                logger.error(f"Found non-integer value in bme values, {temps}")
                                continue

                        self._state.enviro.temperature = int(vals[0])
                        self._state.enviro.humidity = int(vals[2])
                        self._state.enviro.pressure = int(vals[3])
                case _:
                    logger.warning(f"Got a command that isn't supported yet: {cmd} with value {val}")

            if self.on_data:
                self.on_data(cmd, val)

    def _setup_serial(self, port: str, baud: int, timeout: float = 1):
        self.serial = Serial(port, baud, timeout=timeout)
        return self.serial

    def _tick(self):
        if self.serial and self.serial.is_open:
            self.serial.write(b"core.tick\n")


class MqttKevinbot(BaseKevinbot):
    """KevinbotLib interface over MQTT"""

    def __init__(self, cid: str | None = None) -> None:
        """Instansiate a new KevinbotLib interface over MQTT

        Args:
            cid (str | None, optional): MQTT Client id. Defaults to an auto-generated uuid.
        """
        super().__init__()
        self.type = KevinbotConnectionType.MQTT

        self.root_topic = "kevinbot"
        self.host = "localhost"
        self.port = 1883
        self.keepalive = 60
        self.connected = False

        self._hb_thread: Thread | None = None  # thread to produce client's heartbeat
        self._server_hb_thread: Thread | None = None  # thread to check in server heartbeat is slow/stopped

        self._callback: Callable[[list[str], str], Any] | None = None  # message callback
        self._on_server_startup: Callable[[], Any] | None = None
        self._on_server_disconnect: Callable[[], Any] | None = None

        self._eyes: MqttEyes | None = None

        self.cid = cid if cid else f"kevinbotlib-{shortuuid.random()}"  # client id
        self.client = Client(CallbackAPIVersion.VERSION2, self.cid)
        self.client.on_message = self._on_message

        atexit.register(self.disconnect)

    @property
    def callback(self) -> Callable[[list[str], str], Any] | None:
        return self._callback

    @callback.setter
    def callback(self, callback: Callable[[list[str], str], Any] | None) -> None:
        self._callback = callback

    @property
    def on_server_startup(self) -> Callable[[], Any] | None:
        return self._on_server_startup

    @on_server_startup.setter
    def on_server_startup(self, callback: Callable[[], Any] | None) -> None:
        self._on_server_startup = callback

    @property
    def on_server_disconnect(self) -> Callable[[], Any] | None:
        return self._on_server_disconnect

    @on_server_disconnect.setter
    def on_server_disconnect(self, callback: Callable[[], Any] | None) -> None:
        self._on_server_disconnect = callback

    @property
    def mqtt_connected(self) -> bool:
        return self.client.is_connected()

    def connect(
        self,
        root_topic: str = "kevinbot",
        host: str = "localhost",
        port: int = 1883,
        timeout: float = 5.0,
        keepalive: int = 60,
        heartbeat: float = 1.0,
    ) -> MQTTErrorCode:
        """Connect to MQTT Broker

        Args:
            root_topic (str, optional): Root communication topic. Defaults to "kevinbot".
            host (str, optional): KevinbotLib server host. Defaults to "localhost".
            port (int, optional): Kevinbot MQTT Broker port. Defaults to 1883.
            timeout (float, optional): KevinbotLib connection timeout in seconds. Defaults to 5.
            keepalive (int, optional): Maximum period in seconds between communications with the broker. Defaults to 60.
            heartbeat (float, optional): Heartbeat interval in seconds. Defaults to 1.0.

        Returns:
            MQTTErrorCode: Connection error
        """
        self.host = host
        self.port = port
        self.keepalive = keepalive
        self.root_topic = root_topic
        self.connected = False

        self._last_ts_update = datetime.fromtimestamp(0, timezone.utc)
        self._last_server_hb = datetime.fromtimestamp(0, timezone.utc)

        rc = self.client.connect(self.host, self.port, self.keepalive)
        self.client.subscribe(f"{self.root_topic}/state", 0)
        self.client.subscribe(f"{self.root_topic}/eyes/state", 0)
        self.client.subscribe(f"{self.root_topic}/serverstate", 0)
        self.client.subscribe(f"{self.root_topic}/server/startup", 0)
        self.client.subscribe(f"{self.root_topic}/server/shutdown", 0)
        self.client.subscribe(f"{self.root_topic}/clients/connect/ack", 0)
        self.client.loop_start()

        connect_time = time.time()
        while (not self.server_state.mqtt_connected) or (self.server_state.heartbeat_freq == -1):
            time.sleep(0.01)
            if connect_time < time.time() - timeout:
                msg = "KevinbotLib over MQTT handhsake timed out."
                self.client.loop_stop()
                self.client.disconnect()
                raise HandshakeTimeoutException(msg)

        self.connected = True

        self.client.publish(f"{self.root_topic}/clients/connect", self.cid, 0)

        self._hb_thread = Thread(target=self._hb_loop, args=(heartbeat,), daemon=True)
        self._hb_thread.name = f"KevinbotLib.Mqtt.Heartbeat:{self.cid}"
        self._hb_thread.start()

        self._server_hb_thread = Thread(target=self._server_hb_loop, daemon=True)
        self._server_hb_thread.name = f"KevinbotLib.Mqtt.ServerHeartbeat:{self.cid}"
        self._server_hb_thread.start()

        return rc

    def _server_hb_loop(self):
        while True:
            if not self.connected:
                break

            if self.server_state.heartbeat_freq == -1:
                time.sleep(1)
                continue

            if self._last_server_hb < datetime.fromtimestamp(0, timezone.utc) - timedelta(
                seconds=self.server_state.heartbeat_freq
            ):
                # server heartbeat is slow or stopped
                self.connected = False
                if self.on_server_disconnect:
                    self.on_server_disconnect()

            time.sleep(self.server_state.heartbeat_freq)

    def _hb_loop(self, heartbeat: float):
        while True:
            if not self.connected:
                break

            self.client.publish(f"{self.root_topic}/clients/heartbeat", f"{self.cid}:{self.ts.timestamp()}", 0)
            time.sleep(heartbeat)

    def send(self, data: str):
        """Determine topic and publish data. Compatible with send of `SerialKevinbot`

        Args:
            data (str): Data to parse and publish
        """
        if len(data.split("=", 2)) > 1:
            cmd, val = data.split("=", 2)
        else:
            cmd = data
            val = None

        self.client.publish(f"{self.root_topic}/{cmd.replace('.', '/')}", val, 0)

    def disconnect(self):
        """Disconnect from server"""
        super().disconnect()

        if self.mqtt_connected:
            self.client.publish(f"{self.root_topic}/clients/disconnect", self.cid, 0).wait_for_publish(1)
            self.client.loop_stop()
            self.client.disconnect()
        self.connected = False

    def request_enable(self) -> int:
        """Request the core to enable

        Returns:
            int: Always 1
        """
        self.client.publish(f"{self.root_topic}/main/state_request", "enable", 1)
        return 1

    def request_disable(self) -> int:
        """Request the core to disable

        Returns:
            int: Always 1
        """
        self.client.publish(f"{self.root_topic}/main/state_request", "disable", 1)
        return 1

    def e_stop(self):
        """Attempt to send and E-Stop signal to the Core"""
        self.client.publish(f"{self.root_topic}/main/estop", 1)

    @property
    def ts(self) -> datetime:
        """
        Get a semi-accurate timestamp from the server. Used for drivebase timeouts.

        Returns:
            datetime: Server time or UNIX timestamp 0 if server hasn't broadcasted a timestamp yet
        """
        ts = self.server_state.timestamp
        if ts:
            ts += datetime.now(timezone.utc) - self._last_ts_update
            return ts
        return datetime.fromtimestamp(0, timezone.utc)

    def _on_message(self, _, __, msg: MQTTMessage):
        logger.trace(f"Got MQTT message at: {msg.topic} payload={msg.payload!r} with qos={msg.qos}")

        if msg.topic[0] == "/" or msg.topic[-1] == "/":
            logger.warning(f"MQTT topic: {msg.topic} has a leading/trailing slash. Removing it.")
            topic = msg.topic.strip("/")
        else:
            topic = msg.topic

        value = msg.payload.decode("utf-8")

        subtopics = topic.split("/")[1:]
        match subtopics:
            case ["state"]:
                self._state = KevinbotState(**json.loads(value))
            case ["eyes", "state"]:
                if self._eyes:
                    self._eyes._load_data(value)  # noqa: SLF001
            case ["serverstate"]:
                new_state = KevinbotServerState(**json.loads(value))

                if self._server_state.timestamp != new_state.timestamp:
                    self._last_ts_update = datetime.now(timezone.utc)

                self._server_state = new_state
            case ["server", "startup"]:
                # we must reconnect
                self.client.publish(f"{self.root_topic}/clients/connect", self.cid, 0)
                self.connected = True

                if self.on_server_startup:
                    self.on_server_startup()
            case ["server", "shutdown"]:
                self.connected = False
                if self.on_server_disconnect:
                    self.on_server_disconnect()
            case ["clients", "connect", "ack"]:
                if value == f"ack:{self.cid}":
                    self.connected = True

        if self.callback:
            self.callback(subtopics, value)


class Drivebase(BaseKevinbotSubsystem):
    """Drivebase subsystem for Kevinbot"""

    def get_amps(self) -> list[float]:
        """Get the amps being used by the drivebase

        Returns:
            list[float]: Amps
        """
        return self.robot.get_state().motion.amps

    def get_watts(self) -> list[float]:
        """Get the watts being used by the drivebase

        Returns:
            list[float]: Watts
        """
        return self.robot.get_state().motion.watts

    def get_powers(self) -> tuple[int, int]:
        """Get the currently set wheel speeds in percent

        Returns:
            tuple[int, int]: Percent values from 0 to 100
        """
        return self.robot.get_state().motion.left_power, self.robot.get_state().motion.right_power

    def get_states(self) -> list[MotorDriveStatus]:
        """Get the wheels states

        Returns:
            list[MotorDriveStatus]: States
        """
        return self.robot.get_state().motion.status

    def drive_at_power(self, left: float, right: float):
        """Set the drive power for wheels. 0 to 1

        Args:
            left (float): Left motor power
            right (float): Right motor power
        """
        if isinstance(self.robot, SerialKevinbot):
            self.robot.send(f"drive.power={int(left*100)},{int(right*100)}")
        elif isinstance(self.robot, MqttKevinbot):
            self.robot.client.publish(
                f"{self.robot.root_topic}/drive/power",
                f"{int(left*100)},{int(right*100)},{self.robot.cid},{self.robot.ts}",
                1,
            )

    def stop(self):
        """Set all wheel powers to 0"""
        self.drive_at_power(0, 0)


class Servo:
    """Individually controllable servo"""

    def __init__(self, robot: SerialKevinbot | MqttKevinbot, index: int) -> None:
        self.robot = robot
        self.index = index

    @property
    def bank(self) -> int:
        """Get the bank the servo is in

        Returns:
            int: Bank number
        """
        return self.index // 16

    @property
    def angle(self) -> int:
        """Get the optimistic current servo angle

        Returns:
            int: Angle in degrees
        """
        return self.robot.get_state().servos.angles[self.index]

    @angle.setter
    def angle(self, angle: int):
        """Set the optimistic servo angle

        Args:
            angle (int): Angle in degrees
        """
        if isinstance(self.robot, SerialKevinbot):
            self.robot.send(f"s={self.index},{angle}")
        elif isinstance(self.robot, MqttKevinbot):
            self.robot.client.publish(f"{self.robot.root_topic}/servo/set", f"{self.index},{angle}", 0)
        else:
            return

        self.robot.get_state().servos.angles[self.index] = angle


class Servos(BaseKevinbotSubsystem):
    """Servo subsystem for Kevinbot"""

    def __len__(self) -> int:
        """Length will always be 32 since the P2 Kevinbot Board can only control 32

        Returns:
            int: Number of servos in the subsystem
        """
        return 32

    def __iter__(self):
        for i in range(self.__len__()):
            yield Servo(self.robot, i)

    def __getitem__(self, index: int):
        if index > self.__len__():
            msg = f"Servo index {index} > {self.__len__()}"
            raise IndexError(msg)
        if index < 0:
            msg = f"Servo index {index} < 0"
            raise IndexError(msg)
        return Servo(self.robot, index)

    def get_servo(self, channel: int) -> Servo:
        """Get an individual servo in the subsystem

        Args:
            channel (int): PWM Port

        Returns:
            Servo: Individual servo
        """
        if channel > self.__len__() or channel < 0:
            msg = f"Servo channel {channel} is out of bounds."
            raise IndexError(msg)
        return Servo(self.robot, channel)

    @property
    def all(self) -> int:
        if all(i == self.robot.get_state().servos.angles[0] for i in self.robot.get_state().servos.angles):
            return self.robot.get_state().servos.angles[0]
        return -1

    @all.setter
    def all(self, angle: int):
        self.robot.send(f"servo.all={angle}")
        self.robot.get_state().servos.angles = [angle] * self.__len__()


class Lighting(BaseKevinbotSubsystem):
    """Lighting subsystem for Kevinbot"""

    class Channel(Enum):
        """Lighting segment identifier"""

        Head = "head"
        Body = "body"
        Base = "base"

    def get_state(self) -> LightingState:
        """Get the state of the robot's light segments

        Returns:
            LightingState: State
        """
        return self.robot.get_state().lighting

    def set_cam_brightness(self, brightness: int):
        """Set brightness of camera illumination

        Args:
            brightness (int): Brightness from 0 to 255
        """
        self.robot.send(f"lighting.cam.bright={brightness}")
        self.robot.get_state().lighting.camera = brightness

    def set_brightness(self, channel: Channel, brightness: int):
        """Set the brightness of a lighting segment

        Args:
            channel (Channel): Base, Body, or Head
            brightness (int): Brightness from 0 to 255
        """
        self.robot.send(f"lighting.{channel.value}.bright={brightness}")
        match channel:
            case self.Channel.Base:
                self.robot.get_state().lighting.base_bright = brightness
            case self.Channel.Body:
                self.robot.get_state().lighting.body_bright = brightness
            case self.Channel.Head:
                self.robot.get_state().lighting.head_bright = brightness

    def set_color1(self, channel: Channel, color: list[int] | tuple[int, int, int]):
        """Set the Color 1 of a lighting segment

        Args:
            channel (Channel): Base, Body, or Head
            color (Iterable[int]): RGB Color values. Must have a length of 3
        """
        self.robot.send(f"lighting.{channel.value}.color1={color[0]:02x}{color[1]:02x}{color[2]:02x}00")
        match channel:
            case self.Channel.Base:
                self.robot.get_state().lighting.base_color1 = list(color)
            case self.Channel.Body:
                self.robot.get_state().lighting.base_color1 = list(color)
            case self.Channel.Head:
                self.robot.get_state().lighting.base_color1 = list(color)

    def set_color2(self, channel: Channel, color: list[int] | tuple[int, int, int]):
        """Set the Color 2 of a lighting segment

        Args:
            channel (Channel): Base, Body, or Head
            color (Iterable[int]): RGB Color values. Must have a length of 3
        """
        self.robot.send(f"lighting.{channel.value}.color2={color[0]:02x}{color[1]:02x}{color[2]:02x}00")
        match channel:
            case self.Channel.Base:
                self.robot.get_state().lighting.base_color2 = list(color)
            case self.Channel.Body:
                self.robot.get_state().lighting.base_color2 = list(color)
            case self.Channel.Head:
                self.robot.get_state().lighting.base_color2 = list(color)

    def set_effect(self, channel: Channel, effect: str):
        """Set the animation of a lighting segment

        Args:
            channel (Channel): Base, Body, or Head
            effect (str): Animation ID
        """
        self.robot.send(f"lighting.{channel.value}.effect={effect}")
        match channel:
            case self.Channel.Base:
                self.robot.get_state().lighting.base_effect = effect
            case self.Channel.Body:
                self.robot.get_state().lighting.base_effect = effect
            case self.Channel.Head:
                self.robot.get_state().lighting.base_effect = effect

    def set_update(self, channel: Channel, update: int):
        """Set the animation of a lighting segment

        Args:
            channel (Channel): Base, Body, or Head
            update (int): Update rate (no fixed unit)
        """
        self.robot.send(f"lighting.{channel.value}.update={update}")
        match channel:
            case self.Channel.Base:
                self.robot.get_state().lighting.base_update = update
            case self.Channel.Body:
                self.robot.get_state().lighting.base_update = update
            case self.Channel.Head:
                self.robot.get_state().lighting.base_update = update
