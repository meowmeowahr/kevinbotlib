# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import atexit
import json
import time
from collections.abc import Callable
from threading import Thread
from typing import Any

from loguru import logger
from serial import Serial

from kevinbotlib.core import KevinbotConnectionType, MqttKevinbot
from kevinbotlib.exceptions import HandshakeTimeoutException
from kevinbotlib.states import EyeMotion, EyeSettings, EyeSkin, KevinbotEyesState, MetalSkin, NeonSkin, SimpleSkin


class _Simple:
    def __init__(self, skinmgr: "_EyeSkinManager") -> None:
        self.skinmgr = skinmgr

    @property
    def name(self) -> str:
        """Get internal name of skin

        Returns:
            str: Internal name
        """
        return "simple"

    @property
    def bg_color(self) -> str:
        """Get background color of skin

        Returns:
            str: Hex-formatted color code
        """
        return self.skinmgr.eyes.get_state().settings.skins.simple.bg_color

    @bg_color.setter
    def bg_color(self, value: str):
        self.skinmgr.eyes.set_skin_option([self.name, "bg_color", value])

    @property
    def iris_color(self) -> str:
        """Get iris color of skin

        Returns:
            str: Hex-formatted color code
        """
        return self.skinmgr.eyes.get_state().settings.skins.simple.iris_color

    @iris_color.setter
    def iris_color(self, value: str):
        self.skinmgr.eyes.set_skin_option([self.name, "iris_color", value])

    @property
    def pupil_color(self) -> str:
        """Get pupil color of skin

        Returns:
            str: Hex-formatted color code
        """
        return self.skinmgr.eyes.get_state().settings.skins.simple.pupil_color

    @pupil_color.setter
    def pupil_color(self, value: str):
        self.skinmgr.eyes.set_skin_option([self.name, "pupil_color", value])

    @property
    def iris_size(self) -> int:
        """Get iris size of skin

        Returns:
            int: Iris size in pixels
        """
        return self.skinmgr.eyes.get_state().settings.skins.simple.iris_size

    @iris_size.setter
    def iris_size(self, value: int):
        self.skinmgr.eyes.set_skin_option([self.name, "iris_size", value])

    @property
    def pupil_size(self) -> int:
        """Get pupil size of skin

        Returns:
            int: Pupil size in pixels
        """
        return self.skinmgr.eyes.get_state().settings.skins.simple.pupil_size

    @pupil_size.setter
    def pupil_size(self, value: int):
        self.skinmgr.eyes.set_skin_option([self.name, "pupil_size", value])

    def restore(self):
        """Restore simple skin settings to their defaults"""

        self.bg_color = SimpleSkin.bg_color
        self.iris_color = SimpleSkin.iris_color
        self.pupil_color = SimpleSkin.pupil_color
        self.iris_size = SimpleSkin.iris_size
        self.pupil_size = SimpleSkin.pupil_size


class _Metal:
    def __init__(self, skinmgr: "_EyeSkinManager") -> None:
        self.skinmgr = skinmgr

    @property
    def name(self) -> str:
        """Get internal name of skin
        Returns:
        str: Internal name
        """
        return "metal"

    @property
    def bg_color(self) -> str:
        """Get background color of skin
        Returns:
        str: Hex-formatted color code
        """
        return self.skinmgr.eyes.get_state().settings.skins.metal.bg_color

    @bg_color.setter
    def bg_color(self, value: str):
        self.skinmgr.eyes.set_skin_option([self.name, "bg_color", value])

    @property
    def iris_size(self) -> int:
        """Get iris size of skin
        Returns:
        int: Iris size in pixels
        """
        return self.skinmgr.eyes.get_state().settings.skins.metal.iris_size

    @iris_size.setter
    def iris_size(self, value: int):
        self.skinmgr.eyes.set_skin_option([self.name, "iris_size", value])

    @property
    def tint(self) -> int:
        """Get tint value of metal skin
        Returns:
        int: Tint value
        """
        return self.skinmgr.eyes.get_state().settings.skins.metal.tint

    @tint.setter
    def tint(self, value: int):
        self.skinmgr.eyes.set_skin_option([self.name, "tint", value])

    def restore(self):
        """Restore metal skin settings to their defaults"""
        self.bg_color = MetalSkin.bg_color
        self.iris_size = MetalSkin.iris_size
        self.tint = MetalSkin.tint

class _Neon:
    def __init__(self, skinmgr: "_EyeSkinManager") -> None:
        self.skinmgr = skinmgr

    @property
    def name(self) -> str:
        """Get internal name of skin
        Returns:
        str: Internal name
        """
        return "neon"

    @property
    def bg_color(self) -> str:
        """Get background color of skin
        Returns:
        str: Hex-formatted color code
        """
        return self.skinmgr.eyes.get_state().settings.skins.neon.bg_color

    @bg_color.setter
    def bg_color(self, value: str):
        self.skinmgr.eyes.set_skin_option([self.name, "bg_color", value])

    @property
    def iris_size(self) -> int:
        """Get iris size of skin
        Returns:
        int: Iris size in pixels
        """
        return self.skinmgr.eyes.get_state().settings.skins.neon.iris_size

    @iris_size.setter
    def iris_size(self, value: int):
        self.skinmgr.eyes.set_skin_option([self.name, "iris_size", value])

    @property
    def fg_color_start(self) -> str:
        """Get foreground start color of neon skin
        Returns:
        str: Hex-formatted color code
        """
        return self.skinmgr.eyes.get_state().settings.skins.neon.fg_color_start

    @fg_color_start.setter
    def fg_color_start(self, value: str):
        self.skinmgr.eyes.set_skin_option([self.name, "fg_color_start", value])

    @property
    def fg_color_end(self) -> str:
        """Get foreground end color of neon skin
        Returns:
        str: Hex-formatted color code
        """
        return self.skinmgr.eyes.get_state().settings.skins.neon.fg_color_end

    @fg_color_end.setter
    def fg_color_end(self, value: str):
        self.skinmgr.eyes.set_skin_option([self.name, "fg_color_end", value])

    @property
    def style(self) -> str:
        """Get style of neon skin
        Returns:
        str: Filename of internal iris/pupil image
        """
        return self.skinmgr.eyes.get_state().settings.skins.neon.style

    @style.setter
    def style(self, value: str):
        self.skinmgr.eyes.set_skin_option([self.name, "style", value])

    def restore(self):
        """Restore neon skin settings to their defaults"""
        self.bg_color = NeonSkin.bg_color
        self.iris_size = NeonSkin.iris_size
        self.fg_color_start = NeonSkin.fg_color_start
        self.fg_color_end = NeonSkin.fg_color_end
        self.style = NeonSkin.style


class _EyeSkinManager:
    def __init__(self, eyes: "BaseKevinbotEyes") -> None:
        self.eyes = eyes

    @property
    def simple(self) -> _Simple:
        """Get settings for simple eye skin

        Returns:
            _Simple: Settings manager
        """
        return _Simple(self)

    @property
    def metal(self) -> _Metal:
        """Get settings for metal eye skin

        Returns:
            _Metal: Settings manager
        """
        return _Metal(self)

    @property
    def neon(self) -> _Neon:
        """Get settings for neon eye skin

        Returns:
            _Neon: Settings manager
        """
        return _Neon(self)


class BaseKevinbotEyes:
    """The base Kevinbot Eyes class.

    Not to be used directly
    """

    def __init__(self) -> None:
        self._state = KevinbotEyesState()
        self.type = KevinbotConnectionType.BASE

        self._auto_disconnect = True

        self._robot: MqttKevinbot = MqttKevinbot()

    def get_state(self) -> KevinbotEyesState:
        """Gets the current state of the eyes

        Returns:
            KevinbotEyesState: State class
        """
        return self._state

    def disconnect(self):
        """Basic disconnect"""
        self._state.connected = False

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

    def set_skin(self, skin: EyeSkin):
        """Set the current skin

        Args:
            skin (EyeSkin): Skin index
        """
        if isinstance(self, SerialEyes):
            self._state.settings.states.page = skin
            self.send(f"setState={skin.value}")
        elif isinstance(self, MqttEyes):
            self._robot.client.publish(f"{self._robot.root_topic}/eyes/skin", skin.value, 0)

    def set_backlight(self, bl: float):
        """Set the current backlight brightness

        Args:
            bl (float): Brightness from 0 to 1
        """
        if isinstance(self, SerialEyes):
            self._state.settings.display.backlight = min(int(bl * 100), 100)
            self.send(f"setBacklight={self._state.settings.display.backlight}")
        elif isinstance(self, MqttEyes):
            self._robot.client.publish(f"{self._robot.root_topic}/eyes/backlight", int(255 * bl), 0)

    def get_backlight(self):
        """Get the current backlight setting

        Returns:
            float: Value from 0 to 1
        """
        return self._state.settings.display.backlight / 255


    def set_motion(self, motion: EyeMotion):
        """Set the current backlight brightness

        Args:
            motion (EyeMotion): Motion mode
        """
        if isinstance(self, SerialEyes):
            self._state.settings.states.motion = motion
            self.send(f"setMotion={motion.value}")
        elif isinstance(self, MqttEyes):
            self._robot.client.publish(f"{self._robot.root_topic}/eyes/motion", motion.value, 0)

    def set_manual_pos(self, x: int, y: int):
        """Set the on-screen position of pupil

        Args:
            x (int): X Position of pupil
            y (int): Y Position of pupil
        """
        if isinstance(self, SerialEyes):
            self._state.settings.motions.pos = x, y
            self.send(f"setPosition={x},{y}")
        elif isinstance(self, MqttEyes):
            self._robot.client.publish(f"{self._robot.root_topic}/eyes/pos", f"{x},{y}", 0)

    def set_skin_option(self, data: list):
        """Set a raw skin option.

        Args:
            data (list): list of keys, last item is the value
        """
        if len(data) < 3:  # noqa: PLR2004
            logger.error("Data must have at least 2 keys and one value.")
            return

        keys = data[:-1]
        value = data[-1]

        skin_key = keys[0]
        if skin_key not in self._state.settings.skins.model_dump():
            logger.error(f"Invalid skin key: {skin_key}")
            return

        skin = getattr(self._state.settings.skins, skin_key)
        for key in keys[1:]:
            if not hasattr(skin, key):
                logger.error(f"Invalid key '{key}' for skin '{skin_key}'")
                return
            if keys.index(key) == len(keys[1:]) - 1:  # Final attribute to set
                setattr(skin, key, value)
            else:
                skin = getattr(skin, key)

        if isinstance(self, SerialEyes):
            self.send(f"setSkinOption={':'.join(map(str, data))}")
        elif isinstance(self, MqttEyes):
            self._robot.client.publish(f"{self._robot.root_topic}/eyes/skinopt", ":".join(map(str, data)), 0)

    @property
    def skins(self) -> _EyeSkinManager:
        return _EyeSkinManager(self)


class SerialEyes(BaseKevinbotEyes):
    """The main serial Kevinbot Eyes class"""

    def __init__(self) -> None:
        super().__init__()
        self.type = KevinbotConnectionType.SERIAL

        self.serial: Serial | None = None
        self.rx_thread: Thread | None = None

        self._callback: Callable[[str, str | None], Any] | None = None
        self._state_callback: Callable[[KevinbotEyesState], Any] | None = None

        atexit.register(self.disconnect)

    def connect(
        self,
        port: str,
        baud: int,
        timeout: float,
        ser_timeout: float = 0.5,
    ):
        """Start a connection with Kevinbot Eyes

        Args:
            port (str): Serial port to use (`/dev/ttyUSB0` is standard with the typical Kevinbot Hardware)
            baud (int): Baud rate to use (`115200` is typical for the defualt eye configs)
            timeout (float): Timeout for handshake
            ser_timeout (float, optional): Readline timeout, should be lower than `timeout`. Defaults to 0.5.

        Raises:
            HandshakeTimeoutException: Eyes didn't respond to the connection handshake before the timeout
        """
        serial = self._setup_serial(port, baud, ser_timeout)

        start_time = time.monotonic()
        hs_started = False
        while True:
            if not hs_started:
                serial.write(b"connectionReady\n")

            line = serial.readline().decode("utf-8", errors="ignore").strip("\n")

            if line == "handshake.request":
                hs_started = True
                serial.write(b"getSettings=true\n")

            if line == "settTx.done":
                serial.write(b"handshake.complete\n")
                break

            data = line.split("=", 2)
            cmd = line.split("=", 2)[0]
            val = line.split("=", 2)[1] if len(data) > 1 else None

            if cmd.startswith("eyeSettings."):
                # Remove prefix and split into path and value
                setting = cmd[len("eyeSettings.") :]

                path = setting.split(".")

                if not val:
                    logger.error(f"Got eyeSettings command without a value: {cmd} :: {val}")
                    continue

                # Handle array values [x, y]
                if val.startswith("[") and val.endswith("]"):
                    value_str = val.strip("[]")
                    value = tuple(int(x.strip()) for x in value_str.split(","))
                # Handle hex colors
                elif val.startswith("#"):
                    value = val
                # Handle quoted strings
                elif val.startswith('"') and val.endswith('"'):
                    value = val.strip('"')
                # Handle numbers
                else:
                    try:
                        value = int(val)
                    except ValueError:
                        value = val

                # Create a dict representation of the settings
                settings_dict = self._state.settings.model_dump()

                # Navigate to the correct nested dictionary
                current_dict = settings_dict
                for i, key in enumerate(path[:-1]):
                    if key not in current_dict:
                        logger.error(f"Invalid path: {'.'.join(path[:i+1])}")
                        continue
                    if not isinstance(current_dict[key], dict):
                        logger.error(f"Cannot navigate through non-dict value at {'.'.join(path[:i+1])}")
                        continue
                    current_dict = current_dict[key]

                # Update the value
                if path[-1] not in current_dict:
                    logger.error(f"Invalid setting: {'.'.join(path)}")
                    continue
                current_dict[path[-1]] = value

                # Create new settings instance with updated values
                self._state.settings = EyeSettings.model_validate(settings_dict)

            if time.monotonic() - start_time > timeout:
                msg = "Handshake timed out"
                raise HandshakeTimeoutException(msg)

            time.sleep(0.1)  # Avoid spamming the connection

        # Data rx thread
        self.rx_thread = Thread(target=self._rx_loop, args=(serial, "="), daemon=True)
        self.rx_thread.name = "KevinbotLib.Eyes.Rx"
        self.rx_thread.start()

        self._state.connected = True

    def disconnect(self):
        super().disconnect()
        if self.serial and self.serial.is_open:
            self.send("resetConnection")
            self.serial.flush()
            self.serial.close()
        else:
            logger.warning("Already disconnected")

    def update(self):
        """Retrive updated settings from eyes"""

        self.send("getSettings=true")

    @property
    def on_state_updated(self) -> Callable[[KevinbotEyesState], Any] | None:
        return self._state_callback

    @on_state_updated.setter
    def on_state_updated(self, callback: Callable[[KevinbotEyesState], Any] | None):
        self._state_callback = callback

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
            logger.warning(f"Couldn't transmit data: {data!r}, Eyes aren't connected")

    @property
    def callback(self) -> Callable[[str, str | None], Any] | None:
        return self._callback

    @callback.setter
    def callback(self, callback: Callable[[str, str | None], Any]) -> None:
        self._callback = callback

    def _setup_serial(self, port: str, baud: int, timeout: float = 1):
        self.serial = Serial(port, baud, timeout=timeout)
        return self.serial

    def _rx_loop(self, serial: Serial, delimeter: str = "="):
        while True:
            try:
                raw: bytes = serial.readline()
            except TypeError:
                # serial has been stopped
                return

            cmd: str = raw.decode("utf-8").split(delimeter, maxsplit=1)[0].strip().replace("\00", "")
            if not cmd:
                continue

            val: str | None = None
            if len(raw.decode("utf-8").split(delimeter)) > 1:
                val = raw.decode("utf-8").split(delimeter, maxsplit=1)[1].strip("\r\n").replace("\00", "")

            if cmd.startswith("eyeSettings."):
                # Remove prefix and split into path and value
                setting = cmd[len("eyeSettings.") :]

                path = setting.split(".")

                if not val:
                    logger.error(f"Got eyeSettings command without a value: {cmd} :: {val}")
                    continue

                # Handle array values [x, y]
                if val.startswith("[") and val.endswith("]"):
                    value_str = val.strip("[]")
                    value = tuple(int(x.strip()) for x in value_str.split(","))
                # Handle hex colors
                elif val.startswith("#"):
                    value = val
                # Handle quoted strings
                elif val.startswith('"') and val.endswith('"'):
                    value = val.strip('"')
                # Handle numbers
                else:
                    try:
                        value = int(val)
                    except ValueError:
                        value = val

                # Create a dict representation of the settings
                settings_dict = self._state.settings.model_dump()

                # Navigate to the correct nested dictionary
                current_dict = settings_dict
                for i, key in enumerate(path[:-1]):
                    if key not in current_dict:
                        logger.error(f"Invalid path: {'.'.join(path[:i+1])}")
                        continue
                    if not isinstance(current_dict[key], dict):
                        logger.error(f"Cannot navigate through non-dict value at {'.'.join(path[:i+1])}")
                        continue
                    current_dict = current_dict[key]

                # Update the value
                if path[-1] not in current_dict:
                    logger.error(f"Invalid setting: {'.'.join(path)}")
                    continue
                current_dict[path[-1]] = value

                # Create new settings instance with updated values
                self._state.settings = EyeSettings.model_validate(settings_dict)
            else:
                match cmd:
                    case "settTx.done":
                        if self.on_state_updated:
                            self.on_state_updated(self._state)

            if self.callback:
                self.callback(cmd, val)


class MqttEyes(BaseKevinbotEyes):
    """The main serial Kevinbot Eyes class"""

    def __init__(self, robot: MqttKevinbot) -> None:
        super().__init__()
        self.type = KevinbotConnectionType.MQTT

        self.serial: Serial | None = None
        self.rx_thread: Thread | None = None

        self._callback: Callable[[str, str | None], Any] | None = None

        self._robot: MqttKevinbot = robot
        self._robot._eyes = self  # noqa: SLF001

        self._state_loaded = False
        robot.client.publish(f"{robot.root_topic}/eyes/get", "request_settings", 0)

        while not self._state_loaded:
            time.sleep(0.01)

        atexit.register(self.disconnect)

    def update(self):
        """Retrive updated settings from eyes"""

        self._robot.client.publish(f"{self._robot.root_topic}/eyes/get", "request_settings", 0)

    def _load_data(self, data: str):
        self._state_loaded = True
        self._state = KevinbotEyesState(**json.loads(data))
