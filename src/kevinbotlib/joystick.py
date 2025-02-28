import threading
import time
from collections.abc import Callable
from enum import IntEnum
from typing import Any

import sdl2
import sdl2.ext

from kevinbotlib.comm import AnyListSendable, BooleanSendable, IntegerSendable, KevinbotCommClient
from kevinbotlib.exceptions import JoystickMissingException
from kevinbotlib.logger import Logger as _Logger

sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK)


class XboxControllerButtons(IntEnum):
    A = 0
    B = 1
    X = 2
    Y = 3
    LeftBumper = 4
    RightBumper = 5
    Back = 6
    Start = 7
    Guide = 8
    LeftStick = 9
    RightStick = 10
    Share = 11


class XboxControllerAxis(IntEnum):
    """Axis identifiers for Xbox controller."""

    LeftX = 0
    LeftY = 1
    RightX = 3
    RightY = 4
    LeftTrigger = 2
    RightTrigger = 5


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


class RawLocalJoystickDevice:
    """Gamepad-agnostic polling and event-based joystick input with disconnect detection."""

    def __init__(self, index: int, polling_hz: int = 100):
        self.index = index
        self._sdl_joystick: sdl2.joystick.SDL_Joystick = sdl2.SDL_JoystickOpen(index)
        self._logger = _Logger()

        if not self._sdl_joystick:
            msg = f"No joystick of index {index} present"
            raise JoystickMissingException(msg)

        self._logger.info(f"Init joystick {index} of name: {sdl2.SDL_JoystickName(self._sdl_joystick).decode('utf-8')}")
        self._logger.info(
            f"Init joystick {index} of GUID: {''.join(f'{b:02x}' for b in sdl2.SDL_JoystickGetGUID(self._sdl_joystick).data)}"
        )

        self.running = False
        self.connected = False
        self.polling_hz = polling_hz
        self._button_states = {}
        self._button_callbacks = {}
        self._pov_state = POVDirection.NONE
        self._pov_callbacks: list[Callable[[POVDirection], Any]] = []
        self._axis_states = {}
        self._axis_callbacks = {}

        self.on_disconnect: Callable[[], Any] | None = None

        num_axes = sdl2.SDL_JoystickNumAxes(self._sdl_joystick)
        for i in range(num_axes):
            self._axis_states[i] = 0.0

    def get_button_state(self, button_id) -> bool:
        """Returns the state of a button (pressed: True, released: False)."""
        return self._button_states.get(button_id, False)

    def get_axis_value(self, axis_id: int, precision: int = 3) -> float:
        """Returns the current value of the specified axis (-1.0 to 1.0)."""
        return round(max(min(self._axis_states.get(axis_id, 0.0), 1), -1), precision)

    def get_buttons(self) -> list[int]:
        """Returns a list of currently pressed buttons."""
        buttons = [key for key, value in self._button_states.items() if value]
        buttons.sort()
        return buttons

    def get_axes(self, precision: int = 3):
        return [round(max(min(self._axis_states[axis_id], 1), -1), precision) for axis_id in self._axis_states]

    def get_pov_direction(self) -> POVDirection:
        """Returns the current POV (D-pad) direction."""
        return self._pov_state

    def register_button_callback(self, button_id: int, callback: Callable[[bool], Any]) -> None:
        """Registers a callback function for button press/release events."""
        self._button_callbacks[button_id] = callback

    def register_pov_callback(self, callback: Callable[[POVDirection], Any]) -> None:
        """Registers a callback function for POV (D-pad) direction changes."""
        self._pov_callbacks.append(callback)

    def _handle_event(self, event) -> None:
        """Handles SDL events and triggers registered callbacks."""
        if event.type == sdl2.SDL_JOYBUTTONDOWN:
            button = event.jbutton.button
            self._button_states[button] = True
            if button in self._button_callbacks:
                self._button_callbacks[button](True)

        elif event.type == sdl2.SDL_JOYBUTTONUP:
            button = event.jbutton.button
            self._button_states[button] = False
            if button in self._button_callbacks:
                self._button_callbacks[button](False)

        elif event.type == sdl2.SDL_JOYHATMOTION:
            # Convert SDL hat values to angles
            hat_value = event.jhat.value
            new_direction = self._convert_hat_to_direction(hat_value)

            if new_direction != self._pov_state:
                self._pov_state = new_direction
                for callback in self._pov_callbacks:
                    callback(new_direction)

        elif event.type == sdl2.SDL_JOYAXISMOTION:
            axis = event.jaxis.axis
            # Convert SDL axis value (-32768 to 32767) to float (-1.0 to 1.0)
            value = event.jaxis.value / 32767.0

            # For triggers, convert range from [-1.0, 1.0] to [0.0, 1.0]
            if axis in (XboxControllerAxis.LeftTrigger, XboxControllerAxis.RightTrigger):
                value = (value + 1.0) / 2.0

            # Update state and trigger callback if value changed significantly
            self._axis_states[axis] = value
            if axis in self._axis_callbacks:
                self._axis_callbacks[axis](value)

    def _convert_hat_to_direction(self, hat_value: int) -> POVDirection:
        """Converts SDL hat value to POVDirection enum."""
        hat_to_direction = {
            0x00: POVDirection.NONE,  # centered
            0x01: POVDirection.UP,  # up
            0x02: POVDirection.RIGHT,  # right
            0x04: POVDirection.DOWN,  # down
            0x08: POVDirection.LEFT,  # left
            0x03: POVDirection.UP_RIGHT,  # up + right
            0x06: POVDirection.DOWN_RIGHT,  # down + right
            0x0C: POVDirection.DOWN_LEFT,  # down + left
            0x09: POVDirection.UP_LEFT,  # up + left
        }
        return hat_to_direction.get(hat_value, POVDirection.NONE)

    def _event_loop(self):
        """Internal loop for processing SDL events synchronously."""
        while self.running:
            if not sdl2.SDL_JoystickGetAttached(self._sdl_joystick):
                self.connected = False
                self._handle_disconnect()
                self._logger.debug(f"Polling paused, controller {self.index} is disconnected")
            else:
                self.connected = True

            events = sdl2.ext.get_events()
            for event in events:
                if event.type == sdl2.SDL_QUIT:
                    self.running = False
                    break
                self._handle_event(event)

            time.sleep(1 / self.polling_hz)

    def _check_connection(self):
        """Thread to monitor joystick connection state."""
        while self.running:
            if not sdl2.SDL_JoystickGetAttached(self._sdl_joystick):
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
            self._sdl_joystick = sdl2.SDL_JoystickOpen(self.index)
            if self._sdl_joystick and sdl2.SDL_JoystickGetAttached(self._sdl_joystick):
                self._logger.info(f"Reconnected joystick {self.index} successfully")
                return

        time.sleep(1)

    def start_polling(self):
        """Starts the polling loop in a separate thread."""
        if not self.running:
            self.running = True
            threading.Thread(target=self._event_loop, daemon=True).start()
            threading.Thread(target=self._check_connection, daemon=True).start()

    def stop(self):
        """Stops event handling and releases resources."""
        self.running = False
        sdl2.SDL_JoystickClose(self._sdl_joystick)


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
        if trigger not in (XboxControllerAxis.LeftTrigger, XboxControllerAxis.RightTrigger):
            msg = "Invalid trigger specified"
            raise ValueError(msg)
        return max(self.get_axis_value(trigger, precision), 0)

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
    def __init__(
        self, client: KevinbotCommClient, joystick: RawLocalJoystickDevice | LocalXboxController, key: str
    ) -> None:
        self.client = client
        self.joystick = joystick
        self.key = key.rstrip("/")
        self.running = True
        self.thread = threading.Thread(target=self._send_loop(), daemon=True)
        self.thread.start()

    def _send(self):
        self.client.send(self.key + "/buttons", AnyListSendable(value=self.joystick.get_buttons()))
        self.client.send(self.key + "/pov", IntegerSendable(value=self.joystick.get_pov_direction().value))
        self.client.send(self.key + "/axes", AnyListSendable(value=self.joystick.get_axes()))
        self.client.send(self.key + "/connected", BooleanSendable(value=self.joystick.connected))

    def _send_loop(self):
        while self.running:
            self._send()
            time.sleep(1 / self.joystick.polling_hz)

    def stop(self):
        self.running = False
