import math
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum, IntEnum
from typing import Any, final

import sdl2
import sdl2.ext
from pydantic.dataclasses import dataclass

from kevinbotlib._joystick_sdl2_internals import dispatcher as _sdl2_event_dispatcher
from kevinbotlib.comm import (
    AnyListSendable,
    BooleanSendable,
    IntegerSendable,
    RedisCommClient,
)
from kevinbotlib.exceptions import JoystickMissingException
from kevinbotlib.logger import Logger as _Logger

sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_GAMECONTROLLER)


class XboxControllerButtons(IntEnum):
    A = sdl2.SDL_CONTROLLER_BUTTON_A
    B = sdl2.SDL_CONTROLLER_BUTTON_B
    X = sdl2.SDL_CONTROLLER_BUTTON_X
    Y = sdl2.SDL_CONTROLLER_BUTTON_Y
    DpadUp = sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP
    DpadDown = sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN
    DpadLeft = sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT
    DpadRight = sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT
    LeftBumper = sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER
    RightBumper = sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER
    Back = sdl2.SDL_CONTROLLER_BUTTON_BACK
    Start = sdl2.SDL_CONTROLLER_BUTTON_START
    Guide = sdl2.SDL_CONTROLLER_BUTTON_GUIDE
    LeftStick = sdl2.SDL_CONTROLLER_BUTTON_LEFTSTICK
    RightStick = sdl2.SDL_CONTROLLER_BUTTON_RIGHTSTICK
    Share = sdl2.SDL_CONTROLLER_BUTTON_MISC1


class XboxControllerAxis(IntEnum):
    """Axis identifiers for Xbox controller."""

    LeftX = sdl2.SDL_CONTROLLER_AXIS_LEFTX
    LeftY = sdl2.SDL_CONTROLLER_AXIS_LEFTY
    RightX = sdl2.SDL_CONTROLLER_AXIS_RIGHTX
    RightY = sdl2.SDL_CONTROLLER_AXIS_RIGHTY
    LeftTrigger = sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT
    RightTrigger = sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT


class POVDirection(IntEnum):
    """D-pad directions in degrees."""

    UP = 0
    UP_RIGHT = 45
    RIGHT = 90
    DOWN_RIGHT = 135
    DOWN = 180
    DOWN_LEFT = 225
    LEFT = 270
    UP_LEFT = 315
    NONE = -1


@dataclass
class ControllerMap:
    """Controller mapping for joystick events."""

    button_map: dict[int, int]
    axis_map: dict[int, int]

    def map_button(self, button_id: int) -> int:
        if button_id not in self.button_map:
            return button_id
        return self.button_map[button_id]

    def map_axis(self, axis_id: int) -> int:
        if axis_id not in self.axis_map:
            return axis_id
        return self.axis_map[axis_id]


DefaultControllerMap = ControllerMap({}, {})


class LocalJoystickIdentifiers:
    """Static class to handle joystick identification queries."""

    @staticmethod
    def get_count() -> int:
        """Returns the number of connected joysticks."""
        sdl2.SDL_JoystickUpdate()
        return sdl2.SDL_NumJoysticks()

    @staticmethod
    def get_names() -> dict[int, str]:
        """Returns a dictionary of joystick indices and their corresponding names."""
        sdl2.SDL_JoystickUpdate()
        num_joysticks = sdl2.SDL_NumJoysticks()
        joystick_names = {}
        for index in range(num_joysticks):
            joystick_names[index] = sdl2.SDL_JoystickNameForIndex(index).decode("utf-8")
        return joystick_names

    @staticmethod
    def get_guids() -> dict[int, bytes]:
        """Returns a dictionary of joystick indices and their corresponding GUIDs."""
        sdl2.SDL_JoystickUpdate()
        num_joysticks = sdl2.SDL_NumJoysticks()
        joystick_guids = {}
        for index in range(num_joysticks):
            joystick_guids[index] = bytes(sdl2.SDL_JoystickGetGUID(sdl2.SDL_JoystickOpen(index)).data)
        return joystick_guids


class AbstractJoystickInterface(ABC):
    def __init__(self) -> None:
        super().__init__()

        self.polling_hz = 100
        self.connected = False
        self._controller_map: ControllerMap = DefaultControllerMap

    @abstractmethod
    def apply_map(self, controller_map: ControllerMap):
        raise NotImplementedError

    @property
    def controller_map(self):
        return self._controller_map

    @abstractmethod
    def get_button_state(self, button_id: int | Enum | IntEnum) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_axis_value(self, axis_id: int, precision: int = 3) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_buttons(self) -> list[int | Enum | IntEnum]:
        raise NotImplementedError

    @abstractmethod
    def get_axes(self) -> list[int | Enum | IntEnum]:
        raise NotImplementedError

    @abstractmethod
    def get_pov_direction(self) -> POVDirection:
        raise NotImplementedError

    @abstractmethod
    def register_button_callback(self, button_id: int | Enum | IntEnum, callback: Callable[[bool], Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def register_pov_callback(self, callback: Callable[[POVDirection], Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_connected(self) -> bool:
        return False


class NullJoystick(AbstractJoystickInterface):
    def get_button_state(self, _: int | Enum | IntEnum) -> bool:
        return False

    def get_axis_value(self, _: int, __: int = 3) -> float:
        return 0.0

    def get_buttons(self) -> list[int | Enum | IntEnum]:
        return []

    def get_axes(self) -> list[int | Enum | IntEnum]:
        return []

    def get_pov_direction(self) -> POVDirection:
        return POVDirection.NONE

    def register_button_callback(self, _: int | Enum | IntEnum, __: Callable[[bool], Any]) -> None:
        return

    def register_pov_callback(self, _: Callable[[POVDirection], Any]) -> None:
        return

    def is_connected(self) -> bool:
        return super().is_connected()

    def apply_map(self, _controller_map: ControllerMap):
        return


class RawLocalJoystickDevice(AbstractJoystickInterface):
    """Gamepad-agnostic polling and event-based joystick input with disconnect detection."""

    def __init__(self, index: int, polling_hz: int = 100):
        super().__init__()
        self.index = index
        self._sdl_joystick: sdl2.joystick.SDL_Joystick = sdl2.SDL_GameControllerOpen(index)
        self.guid = bytes(sdl2.SDL_JoystickGetGUID(sdl2.SDL_GameControllerGetJoystick(self._sdl_joystick)).data)
        self._logger = _Logger()

        if not self._sdl_joystick:
            msg = f"No joystick of index {index} present"
            raise JoystickMissingException(msg)

        self._logger.info(f"Init joystick {index} of name: {sdl2.SDL_GameControllerName(self._sdl_joystick).decode('utf-8')}")
        self._logger.info(
            f"Init joystick {index} of GUID: {''.join(f'{b:02x}' for b in sdl2.SDL_JoystickGetGUID(sdl2.SDL_GameControllerGetJoystick(self._sdl_joystick)).data)}"
        )

        self.running = False
        self.connected = False
        self.polling_hz = polling_hz
        self._button_states = {}
        self._button_callbacks = {}
        self._pov_state = POVDirection.NONE
        self._pov_buttons = []
        self._pov_callbacks: list[Callable[[POVDirection], Any]] = []
        self._axis_states = {}
        self._axis_callbacks = {}
        self._controller_map: ControllerMap = DefaultControllerMap

        self.on_disconnect: Callable[[], Any] | None = None

        num_axes = sdl2.SDL_CONTROLLER_AXIS_MAX
        for i in range(num_axes):
            self._axis_states[i] = 0.0

    def is_connected(self) -> bool:
        return self.connected

    def get_button_count(self) -> int:
        """Returns the total number of buttons on the joystick."""
        if not self._sdl_joystick or not sdl2.SDL_GameControllerGetAttached(self._sdl_joystick):
            return 0
        return sdl2.SDL_CONTROLLER_BUTTON_MAX

    def get_button_state(self, button_id: int) -> bool:
        """Returns the state of a button (pressed: True, released: False)."""
        return self._button_states.get(self._controller_map.map_button(button_id), False)

    def get_axis_value(self, axis_id: int, precision: int = 3) -> float:
        """Returns the current value of the specified axis (-1.0 to 1.0)."""
        return round(max(min(self._axis_states.get(self._controller_map.map_axis(axis_id), 0.0), 1), -1), precision)

    def get_buttons(self) -> list[int]:
        """Returns a list of currently pressed buttons."""
        buttons = [self._controller_map.map_button(key) for key, value in self._button_states.items() if value]
        buttons.sort()
        return buttons

    def get_axes(self, precision: int = 3):
        return [
            round(
                float(
                    max(
                        min(self._axis_states[self._controller_map.map_axis(axis_id)], 1),
                        -1,
                    )
                ),
                precision,
            )
            for axis_id in self._axis_states
        ]

    def get_pov_direction(self) -> POVDirection:
        """Returns the current POV (D-pad) direction."""
        return self._pov_state

    def rumble(self, low_power: float, high_power: float, duration: float):
        sdl2.SDL_GameControllerRumble(
            self._sdl_joystick, int(low_power * 65535), int(high_power * 65535), int(duration * 1000)
        )

    def register_button_callback(self, button_id: int, callback: Callable[[bool], Any]) -> None:
        """Registers a callback function for button press/release events."""
        self._button_callbacks[button_id] = callback

    def register_pov_callback(self, callback: Callable[[POVDirection], Any]) -> None:
        """Registers a callback function for POV (D-pad) direction changes."""
        self._pov_callbacks.append(callback)

    def apply_map(self, controller_map: ControllerMap):
        self._controller_map = controller_map

    def _handle_event(self, event) -> None:
        """Handles SDL events and triggers registered callbacks."""
        if event.type == sdl2.SDL_CONTROLLERBUTTONDOWN:
            button = event.cbutton.button
            self._button_states[button] = True
            if self._controller_map.map_button(button) in self._button_callbacks:
                self._button_callbacks[self._controller_map.map_button(button)](True)

            new_direction = self._convert_buttons_to_direction(self.get_buttons())

            if new_direction != self._pov_state:
                self._pov_state = new_direction
                for callback in self._pov_callbacks:
                    callback(new_direction)

        elif event.type == sdl2.SDL_CONTROLLERBUTTONUP:
            button = event.cbutton.button
            self._button_states[button] = False
            if self._controller_map.map_button(button) in self._button_callbacks:
                self._button_callbacks[self._controller_map.map_button(button)](False)

            new_direction = self._convert_buttons_to_direction(self.get_buttons())

            if new_direction != self._pov_state:
                self._pov_state = new_direction
                for callback in self._pov_callbacks:
                    callback(new_direction)

        elif event.type == sdl2.SDL_CONTROLLERAXISMOTION:
            axis = event.caxis.axis
            # Convert SDL axis value (-32,768 to 32,767) to float (-1.0 to 1.0)
            value = event.caxis.value / 32767.0

            # Update state and trigger callback if the value changed significantly
            self._axis_states[axis] = value
            if axis in self._axis_callbacks:
                self._axis_callbacks[axis](value)

    @staticmethod
    def _convert_buttons_to_direction(buttons: list[int]) -> POVDirection:
        """Convert list of buttons to POV direction."""
        if not buttons:
            return POVDirection.NONE

        x = 0
        y = 0
        if sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP in buttons:
            y += 1
        if sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN in buttons:
            y -= 1
        if sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT in buttons:
            x += 1
        if sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT in buttons:
            x -= 1

        if x == 0 and y == 0:
            # Opposing directions cancel out (e.g., up+down)
            return POVDirection.NONE

        # atan2 returns radians CCW from positive X-axis; POV expects degrees CW from up
        rad = math.atan2(x, y)  # Note: args are (x, y), not (y, x) to rotate 90°
        angle = (math.degrees(rad) + 360) % 360
        return POVDirection(int(round(angle)))

    def _event_loop(self):
        """Internal loop for processing SDL events synchronously."""
        while self.running:
            if not sdl2.SDL_GameControllerGetAttached(self._sdl_joystick):
                self.connected = False
                for key in self._axis_states:
                    self._axis_states[key] = 0.0

                self._button_states = {}
                self._pov_state = POVDirection.NONE
                self._handle_disconnect()
                self._logger.debug(f"Polling paused, controller {self.index} is disconnected")
            else:
                self.connected = True

            _sdl2_event_dispatcher().iterate()
            events: list[sdl2.events.SDL_Event] = _sdl2_event_dispatcher().get(
                sdl2.joystick.SDL_JoystickInstanceID(sdl2.SDL_GameControllerGetJoystick(self._sdl_joystick))
            )
            for event in events:
                if event.type == sdl2.SDL_QUIT:
                    self.running = False
                    break
                if event.jdevice.which == sdl2.joystick.SDL_JoystickInstanceID(sdl2.SDL_GameControllerGetJoystick(self._sdl_joystick)):
                    self._handle_event(event)

            time.sleep(1 / self.polling_hz)

    def _check_connection(self):
        """Thread to monitor joystick connection state."""
        while self.running:
            if not sdl2.SDL_GameControllerGetAttached(self._sdl_joystick):
                self._handle_disconnect()
                return
            time.sleep(0.5)

    def _handle_disconnect(self):
        """Handles joystick disconnection."""
        self._logger.warning(f"Joystick {self.index} disconnected.")
        if self.on_disconnect:
            self.on_disconnect()
        self._attempt_reconnect()

    def _attempt_reconnect(self):
        """Attempts to reconnect the joystick."""
        self._logger.info("Attempting to reconnect...")

        self.connected = False
        time.sleep(1)

        num_joysticks = sdl2.SDL_NumJoysticks()
        if self.index < num_joysticks:
            self._sdl_joystick = sdl2.SDL_GameControllerOpen(self.index)
            if self._sdl_joystick and sdl2.SDL_GameControllerGetAttached(self._sdl_joystick):
                self._logger.info(f"Reconnected joystick {self.index} successfully")
                self.guid = bytes(sdl2.SDL_JoystickGetGUID(sdl2.SDL_GameControllerGetJoystick(self._sdl_joystick)).data)
                return

        time.sleep(1)

    def start_polling(self):
        """Starts the polling loop in a separate thread."""
        if not self.running:
            self.running = True
            threading.Thread(
                target=self._event_loop,
                daemon=True,
                name=f"KevinbotLib.Joystick.EvLoop.{self.index}",
            ).start()
            threading.Thread(
                target=self._check_connection,
                daemon=True,
                name=f"KevinbotLib.Joystick.ConnCheck.{self.index}",
            ).start()

    def stop(self):
        """Stops event handling and releases resources."""
        self.running = False
        sdl2.SDL_GameControllerClose(self._sdl_joystick)


class LocalXboxController(RawLocalJoystickDevice):
    """Xbox-specific controller with button name mappings."""

    def get_button_state(self, button: XboxControllerButtons) -> bool:
        """Returns the state of a button using its friendly name."""
        return super().get_button_state(button)

    def get_buttons(self) -> list[XboxControllerButtons]:
        return [XboxControllerButtons(x) for x in super().get_buttons()]

    def register_button_callback(self, button: XboxControllerButtons, callback: Callable[[bool], Any]) -> None:
        """Registers a callback using the friendly button name."""
        super().register_button_callback(button, callback)

    def get_dpad_direction(self) -> POVDirection:
        """Returns the current D-pad direction using Xbox terminology."""
        return self.get_pov_direction()

    def get_trigger_value(self, trigger: XboxControllerAxis, precision: int = 3) -> float:
        """Returns the current value of the specified trigger (0.0 to 1.0)."""
        if trigger not in (
            XboxControllerAxis.LeftTrigger,
            XboxControllerAxis.RightTrigger,
        ):
            msg = "Invalid trigger specified"
            raise ValueError(msg)
        return (max(self.get_axis_value(trigger, precision), 0) + 1) / 2

    def get_axis_value(self, axis_id: int, precision: int = 3) -> float:
        return super().get_axis_value(axis_id, precision)

    def get_triggers(self, precision: int = 3):
        return [
            self.get_trigger_value(XboxControllerAxis.LeftTrigger, precision),
            self.get_trigger_value(XboxControllerAxis.RightTrigger, precision),
        ]

    def get_left_stick(self, precision: int = 3):
        return [
            self.get_axis_value(XboxControllerAxis.LeftX, precision),
            self.get_axis_value(XboxControllerAxis.LeftY, precision),
        ]

    def get_right_stick(self, precision: int = 3):
        return [
            self.get_axis_value(XboxControllerAxis.RightX, precision),
            self.get_axis_value(XboxControllerAxis.RightY, precision),
        ]

    def register_dpad_callback(self, callback: Callable[[POVDirection], Any]) -> None:
        """Registers a callback for D-pad direction changes using Xbox terminology."""
        self.register_pov_callback(callback)


class JoystickSender:
    def __init__(self, client: RedisCommClient, joystick: AbstractJoystickInterface, key: str) -> None:
        self.client = client

        self.joystick = joystick

        self.key = key.rstrip("/")

        self.running = False

    @final
    def _send(self):
        self.client.set(self.key + "/buttons", AnyListSendable(value=self.joystick.get_buttons()))
        self.client.set(
            self.key + "/pov",
            IntegerSendable(value=self.joystick.get_pov_direction().value),
        )
        self.client.set(self.key + "/axes", AnyListSendable(value=self.joystick.get_axes()))
        self.client.set(self.key + "/connected", BooleanSendable(value=self.joystick.is_connected()))

    @final
    def _send_loop(self):
        while self.running:
            self._send()
            time.sleep(1 / self.joystick.polling_hz)

    @final
    def start(self):
        self.running = True
        self.thread = threading.Thread(
            target=self._send_loop,
            daemon=True,
            name="KevinbotLib.Joysticks.CommSender",
        )
        self.thread.start()

    @final
    def stop(self):
        self.running = False


class DynamicJoystickSender:
    def __init__(
        self, client: RedisCommClient, joystick_getter: Callable[[], AbstractJoystickInterface], key: str
    ) -> None:
        self.client = client

        self.joystick = joystick_getter

        self.key = key.rstrip("/")

        self.running = False

    @final
    def _send(self):
        self.client.set(self.key + "/buttons", AnyListSendable(value=self.joystick().get_buttons()))
        self.client.set(
            self.key + "/pov",
            IntegerSendable(value=self.joystick().get_pov_direction().value),
        )
        self.client.set(self.key + "/axes", AnyListSendable(value=self.joystick().get_axes()))
        self.client.set(self.key + "/connected", BooleanSendable(value=self.joystick().is_connected()))

    @final
    def _send_loop(self):
        while self.running:
            self._send()
            time.sleep(1 / self.joystick().polling_hz)

    @final
    def start(self):
        self.running = True
        self.thread = threading.Thread(
            target=self._send_loop,
            daemon=True,
            name="KevinbotLib.Joysticks.CommSender",
        )
        self.thread.start()

    @final
    def stop(self):
        self.running = False


class RemoteRawJoystickDevice(AbstractJoystickInterface):
    def __init__(self, client: RedisCommClient, key: str, callback_polling_hz: int = 100) -> None:
        super().__init__()
        self._client: RedisCommClient = client
        self._client_key: str = key.rstrip("/")
        self.polling_hz = callback_polling_hz

        # Callback storage
        self._button_callbacks = {}
        self._pov_callbacks: list[Callable[[POVDirection], Any]] = []
        self._axis_callbacks = {}

        # State tracking for callback triggering
        self._last_button_states = {}
        self._last_pov_state = POVDirection.NONE
        self._last_axis_states = {}

        self._controller_map: ControllerMap = DefaultControllerMap

        self.connected = False
        self.running = False

        # Start the polling thread
        self.start_polling()

    @property
    def client(self) -> RedisCommClient:
        return self._client

    @property
    def key(self) -> str:
        return self._client_key

    def is_connected(self) -> bool:
        sendable = self.client.get(f"{self._client_key}/connected", BooleanSendable)
        if not sendable:
            return False
        return sendable.value

    def get_button_state(self, button_id: int | Enum | IntEnum) -> bool:
        sendable = self.client.get(f"{self._client_key}/buttons", AnyListSendable)
        if not sendable:
            return False
        mapped_id = self._controller_map.map_button(button_id)
        return mapped_id in sendable.value

    def get_axis_value(self, axis_id: int, precision: int = 3) -> float:
        sendable = self.client.get(f"{self._client_key}/axes", AnyListSendable)
        if not sendable:
            return 0.0
        mapped_id = self._controller_map.map_axis(axis_id)
        return round(sendable.value[mapped_id], precision) if mapped_id < len(sendable.value) else 0.0

    def get_buttons(self) -> list[int | Enum | IntEnum]:
        sendable = self.client.get(f"{self._client_key}/buttons", AnyListSendable)
        if not sendable:
            return []
        # Map received button IDs back through the controller map
        return [self._controller_map.map_button(btn) for btn in sendable.value]

    def get_axes(self) -> list[float]:
        sendable = self.client.get(f"{self._client_key}/axes", AnyListSendable)
        if not sendable:
            return []
        # Map received axis values through the controller map
        axes = [0.0] * len(sendable.value)
        for i in range(len(sendable.value)):
            mapped_id = self._controller_map.map_axis(i)
            if mapped_id < len(sendable.value):
                axes[mapped_id] = sendable.value[i]
        return axes

    def get_pov_direction(self) -> POVDirection:
        sendable = self.client.get(f"{self._client_key}/pov", IntegerSendable)
        if not sendable:
            return POVDirection.NONE
        return POVDirection(sendable.value)

    def register_button_callback(self, button_id: int | Enum | IntEnum, callback: Callable[[bool], Any]) -> None:
        """Registers a callback function for button press/release events."""
        self._button_callbacks[button_id] = callback

    def register_pov_callback(self, callback: Callable[[POVDirection], Any]) -> None:
        """Registers a callback function for POV (D-pad) direction changes."""
        self._pov_callbacks.append(callback)

    def apply_map(self, controller_map: ControllerMap):
        self._controller_map = controller_map

    def _poll_loop(self):
        """Polling loop that checks for state changes and triggers callbacks."""
        while self.running:
            # Check connection status
            conn_sendable = self.client.get(f"{self._client_key}/connected", BooleanSendable)
            self.connected = conn_sendable.value if conn_sendable else False

            if self.connected:
                # Check buttons
                buttons = self.get_buttons()
                current_button_states = {btn: True for btn in buttons}

                # Check for button state changes
                for button in set(self._last_button_states.keys()) | set(current_button_states.keys()):
                    old_state = self._last_button_states.get(button, False)
                    new_state = current_button_states.get(button, False)

                    if old_state != new_state and self._controller_map.map_button(button) in self._button_callbacks:
                        self._button_callbacks[self._controller_map.map_button(button)](new_state)

                self._last_button_states = current_button_states

                # Check POV
                current_pov = self.get_pov_direction()
                if current_pov != self._last_pov_state:
                    for callback in self._pov_callbacks:
                        callback(current_pov)
                self._last_pov_state = current_pov

            time.sleep(1 / self.polling_hz)

    def start_polling(self):
        """Starts the polling loop in a separate thread."""
        if not self.running:
            self.running = True
            threading.Thread(
                target=self._poll_loop,
                daemon=True,
                name="KevinbotLib.Joystick.Remote.Poll",
            ).start()

    def stop(self):
        """Stops the polling thread."""
        self.running = False


class RemoteXboxController(RemoteRawJoystickDevice):
    """Xbox-specific remote controller with button name mappings."""

    def __init__(self, client: RedisCommClient, key: str, callback_polling_hz: int = 100) -> None:
        super().__init__(client, key, callback_polling_hz)

    def get_button_state(self, button: XboxControllerButtons) -> bool:
        """Returns the state of a button using its friendly Xbox name."""
        return super().get_button_state(button)

    def get_buttons(self) -> list[XboxControllerButtons]:
        """Returns a list of currently pressed buttons using Xbox button enums."""
        buttons = []
        for x in super().get_buttons():
            try:
                buttons.append(XboxControllerButtons(x))
            except ValueError:
                _Logger().error(f"Invalid button value received: {x}, not in XboxControllerButtons")
        return buttons

    def get_axes(self, precision: int = 3) -> list[float]:
        """Returns a list of axis values with Xbox-specific ordering."""
        axes = super().get_axes()
        if not axes:
            return [0.0] * len(XboxControllerAxis)  # Return default zeroed axes if no data
        return [round(x, precision) for x in axes]  # Convert to float and apply precision

    def register_button_callback(self, button: XboxControllerButtons, callback: Callable[[bool], Any]) -> None:
        """Registers a callback using the friendly Xbox button name."""
        super().register_button_callback(button, callback)

    def register_dpad_callback(self, callback: Callable[[POVDirection], Any]) -> None:
        """Registers a callback for D-pad direction changes using Xbox terminology."""
        super().register_pov_callback(callback)

    def get_dpad_direction(self) -> POVDirection:
        """Returns the current D-pad direction using Xbox terminology."""
        return super().get_pov_direction()

    def get_trigger_value(self, trigger: XboxControllerAxis, precision: int = 3) -> float:
        """Returns the current value of the specified trigger (0.0 to 1.0)."""
        if trigger not in (
            XboxControllerAxis.LeftTrigger,
            XboxControllerAxis.RightTrigger,
        ):
            msg = "Invalid trigger specified"
            raise ValueError(msg)
        value = super().get_axis_value(trigger, precision)
        return (max(value, 0.0) + 1) / 2  # Ensure triggers are 0.0 to 1.0

    def get_triggers(self, precision: int = 3) -> list[float]:
        """Returns the current values of both triggers."""
        return [
            self.get_trigger_value(XboxControllerAxis.LeftTrigger, precision),
            self.get_trigger_value(XboxControllerAxis.RightTrigger, precision),
        ]

    def get_left_stick(self, precision: int = 3) -> list[float]:
        """Returns the current values of the left stick (x, y)."""
        return [
            super().get_axis_value(XboxControllerAxis.LeftX, precision),
            super().get_axis_value(XboxControllerAxis.LeftY, precision),
        ]

    def get_right_stick(self, precision: int = 3) -> list[float]:
        """Returns the current values of the right stick (x, y)."""
        return [
            super().get_axis_value(XboxControllerAxis.RightX, precision),
            super().get_axis_value(XboxControllerAxis.RightY, precision),
        ]

    def _poll_loop(self):
        """Xbox-specific polling loop that checks for state changes and triggers callbacks."""
        while self.running:
            # Check connection status
            conn_sendable = self.client.get(f"{self._client_key}/connected", BooleanSendable)
            self.connected = conn_sendable.value if conn_sendable else False

            if self.connected:
                # Check buttons
                buttons = self.get_buttons()
                current_button_states = {btn: True for btn in buttons}

                # Check for button state changes
                for button in set(self._last_button_states.keys()) | set(current_button_states.keys()):
                    old_state = self._last_button_states.get(button, False)
                    new_state = current_button_states.get(button, False)

                    if old_state != new_state and button in self._button_callbacks:
                        self._button_callbacks[button](new_state)

                self._last_button_states = current_button_states

                # Check POV/D-pad
                current_pov = self.get_dpad_direction()
                if current_pov != self._last_pov_state:
                    for callback in self._pov_callbacks:
                        callback(current_pov)
                self._last_pov_state = current_pov

                # Check axes (only update states here, specific methods handle formatting)
                current_axes = super().get_axes()
                for axis_id in range(len(current_axes)):
                    self._last_axis_states[axis_id] = current_axes[axis_id]

            time.sleep(1 / self.polling_hz)
