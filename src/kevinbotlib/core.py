# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import atexit
import logging
import re
import time
from enum import Enum
from threading import Thread

import shortuuid
from loguru import logger
from paho.mqtt.client import CallbackAPIVersion, Client, MQTTErrorCode  # type: ignore
from serial import Serial

from kevinbotlib.exceptions import HandshakeTimeoutException
from kevinbotlib.misc import Temperature
from kevinbotlib.states import BmsBatteryState, KevinbotState, LightingState, MotorDriveStatus


class BaseKevinbotSubsystem:
    """The base subsystem class.

    Not to be used directly
    """

    def __init__(self, robot: "SerialKevinbot") -> None:
        self.robot = robot
        self.robot._register_component(self)  # noqa: SLF001


class BaseKevinbot:
    """The base robot class.

    Not to be used directly
    """

    def __init__(self) -> None:
        self._state = KevinbotState()
        self._subsystems: list[BaseKevinbotSubsystem] = []

        self._auto_disconnect = True
        atexit.register(self.disconnect)

    def get_state(self) -> KevinbotState:
        """Gets the current state of the robot

        Returns:
            KevinbotState: State class
        """
        return self._state

    def disconnect(self):
        """Basic robot disconnect"""
        self._state.connected = False
        self.send("core.link.unlink")

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

    def _register_component(self, component: BaseKevinbotSubsystem):
        self._subsystems.append(component)


class SerialKevinbot(BaseKevinbot):
    """The main serial robot class"""

    def __init__(self) -> None:
        super().__init__()

        self.serial: Serial | None = None
        self.rx_thread: Thread | None = None

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
            self.serial.flush()
            self.serial.close()
        else:
            logger.warning("Already disconnected")

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

            cmd: str = raw.decode("utf-8").split(delimeter, maxsplit=1)[0]

            val: str | None = None
            if len(raw.decode("utf-8").split(delimeter)) > 1:
                val = raw.decode("utf-8").split(delimeter, maxsplit=1)[1].strip("\r\n")

            match cmd:
                case "ready\n":
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
                case "motors.amps":
                    if val:
                        self._state.motion.amps = list(map(float, val.split(",")))
                case "motors.watts":
                    if val:
                        self._state.motion.watts = list(map(float, val.split(",")))
                case "motors.status":
                    if val:
                        self._state.motion.status = [MotorDriveStatus(int(x)) for x in val.split(",")]
                case "bms.voltages":
                    if val:
                        self._state.battery.voltages = [float(x) / 10 for x in val.split(",")]
                case "bms.raw_voltages":
                    if val:
                        self._state.battery.raw_voltages = [float(x) / 10 for x in val.split(",")]
                case "bms.status":
                    if val:
                        self._state.battery.states = [BmsBatteryState(int(x)) for x in val.split(",")]
                case "sensors.gyro":
                    if val:
                        self._state.imu.gyro = [int(x) for x in val.split(",")]
                case "sensors.accel":
                    if val:
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
                            self._state.thermal.left_motor = Temperature(int(temps[0]) / 100)
                            self._state.thermal.right_motor = Temperature(int(temps[1]) / 100)
                            self._state.thermal.internal = Temperature(int(temps[2]) / 100)
                case "sensors.bme":
                    if val:
                        vals = val.split(",")
                        for value in vals:
                            if not re.match("^[-+]?[0-9]+$", value):
                                logger.error(f"Found non-integer value in bme values, {temps}")
                                continue

                        self._state.enviro.temperature = Temperature(int(vals[0]))
                        self._state.enviro.humidity = int(vals[2])
                        self._state.enviro.pressure = int(vals[3])
                case _:
                    logger.warning(f"Got a command that isn't supported yet: {cmd} with value {val}")

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

        self.root_topic = "kevinbot"
        self.host = "localhost"
        self.port = 1883
        self.keepalive = 60

        self.cid = cid if cid else f"kevinbotlib-{shortuuid.random()}"
        self.client = Client(CallbackAPIVersion.VERSION2, self.cid)
        self.client.loop_start()

    def connect(
        self, root_topic: str = "kevinbot", host: str = "localhost", port: int = 1883, keepalive: int = 60
    ) -> MQTTErrorCode:
        """Connect to MQTT Broker

        Args:
            root_topic (str, optional): Root communication topic. Defaults to "kevinbot".
            host (str, optional): KevinbotLib server host. Defaults to "localhost".
            port (int, optional): Kevinbot MQTT Broker port. Defaults to 1883.
            keepalive (int, optional): Maximum period in seconds between communications with the broker. Defaults to 60.

        Returns:
            MQTTErrorCode: Connection error
        """
        self.host = host
        self.port = port
        self.keepalive = keepalive
        self.root_topic = root_topic

        return self.client.connect(self.host, self.port, self.keepalive)
    

    def send(self, data: str):
        """Determine topic and publish data. Compatible with send of `SerialKevinbot`

        Args:
            data (str): Data to parse and publish
        """
        cmd, val = data.split("=", 2)

        match cmd:
            case "kevinbot.tryenable": qos = 1
            case "system.estop": qos = 1
            case _: qos = 0

        self.client.publish(f"{self.root_topic}/{cmd.replace('.', '/')}/cmd", val, qos)


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
        self.robot.send(f"drive.power={int(left*100)},{int(right*100)}")

    def stop(self):
        """Set all wheel powers to 0"""
        self.robot.send("drive.stop")


class Servo:
    """Individually controllable servo"""

    def __init__(self, robot: SerialKevinbot, index: int) -> None:
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
        self.robot.send(f"s={self.index},{angle}")
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
                self.robot.get_state().lighting.base_color1 = color
            case self.Channel.Body:
                self.robot.get_state().lighting.base_color1 = color
            case self.Channel.Head:
                self.robot.get_state().lighting.base_color1 = color

    def set_color2(self, channel: Channel, color: list[int] | tuple[int, int, int]):
        """Set the Color 2 of a lighting segment

        Args:
            channel (Channel): Base, Body, or Head
            color (Iterable[int]): RGB Color values. Must have a length of 3
        """
        self.robot.send(f"lighting.{channel.value}.color2={color[0]:02x}{color[1]:02x}{color[2]:02x}00")
        match channel:
            case self.Channel.Base:
                self.robot.get_state().lighting.base_color2 = color
            case self.Channel.Body:
                self.robot.get_state().lighting.base_color2 = color
            case self.Channel.Head:
                self.robot.get_state().lighting.base_color2 = color

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
