import threading
import time
from enum import IntEnum
from typing import TYPE_CHECKING, Any

import sdl2
import sdl2.ext

from kevinbotlib.exceptions import JoystickMissingException
from kevinbotlib.logger import Logger as _Logger

if TYPE_CHECKING:
    from collections.abc import Callable

sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK)  # initialize the SDL2 joystick subsystem


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
        self.polling_hz = polling_hz
        self._button_states = {}
        self._button_callbacks = {}
        self.on_disconnect: Callable[[], Any] | None = None  # Callback when joystick disconnects

    def get_button_state(self, button_id):
        """Returns the state of a button (pressed: True, released: False)."""
        return self._button_states.get(button_id, False)

    def get_buttons(self):
        return [key for key, value in self._button_states.items() if value]

    def register_button_callback(self, button_id, callback):
        """Registers a callback function for button press/release events."""
        self._button_callbacks[button_id] = callback

    def _handle_event(self, event):
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

    def _event_loop(self):
        """Internal loop for processing SDL events synchronously."""
        while self.running:
            if not sdl2.SDL_JoystickGetAttached(self._sdl_joystick):
                self._handle_disconnect()
                self._logger.debug(f"Polling paused, controller {self.index} is disconnected")

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

        # Refresh SDL joystick system
        sdl2.SDL_QuitSubSystem(sdl2.SDL_INIT_JOYSTICK)
        time.sleep(1)  # Give SDL time to process device removal
        sdl2.SDL_InitSubSystem(sdl2.SDL_INIT_JOYSTICK)

        # Check if joystick is available before opening
        num_joysticks = sdl2.SDL_NumJoysticks()
        if self.index < num_joysticks:
            self._sdl_joystick = sdl2.SDL_JoystickOpen(self.index)
            if self._sdl_joystick and sdl2.SDL_JoystickGetAttached(self._sdl_joystick):
                self._logger.info(f"Reconnected joystick {self.index} successfully")
                return

        time.sleep(1)  # Wait before retrying

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

    def get_button_state(self, button: XboxControllerButtons):
        """Returns the state of a button using its friendly name."""
        return super().get_button_state(button)

    def register_button_callback(self, button: XboxControllerButtons, callback):
        """Registers a callback using the friendly button name."""
        super().register_button_callback(button, callback)
