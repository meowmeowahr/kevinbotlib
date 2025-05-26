import math
import multiprocessing
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Any, final

import sdl2

from kevinbotlib.comm import (
    AnyListSendable,
    BooleanSendable,
    IntegerSendable,
    RedisCommClient,
)
from kevinbotlib.exceptions import JoystickMissingException
from kevinbotlib.logger import Level
from kevinbotlib.logger import Logger as _Logger
from kevinbotlib.multiprocessing import SafeTelemeterizedProcess

import pygame

pygame.init()
pygame.joystick.init()

class LocalJoystickIdentifiers:
    """Static class to handle joystick identification queries."""

    @staticmethod
    def get_count() -> int:
        """Returns the number of connected joysticks."""
        sdl2.SDL_JoystickUpdate()
        return pygame.joystick.get_count()


class AbstractJoystickInterface(ABC):
    def __init__(self) -> None:
        super().__init__()

        self.polling_hz = 100
        self.connected = False

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
    def get_pov_direction(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def register_button_callback(self, button_id: int, callback: Callable[[bool], Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def register_pov_callback(self, callback: Callable[[int], Any]) -> None:
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

    def get_pov_direction(self) -> int:
        return -1

    def is_connected(self) -> bool:
        return super().is_connected()

import pygame
import threading
import time
import math
from enum import IntEnum
from dataclasses import dataclass
from typing import Callable, Any
from collections import deque


class RawLocalJoystickDevice:
    """Gamepad-agnostic polling and event-based joystick input with disconnect detection using pygame."""

    class ButtonSignal(IntEnum):
        Pressed = 1
        Released = 2

    @dataclass
    class GameControllerEvent:
        identifier: int | None
        timestamp: int | None

    @dataclass
    class ButtonEvent(GameControllerEvent):
        button_id: int
        button_signal: "RawLocalJoystickDevice.ButtonSignal"

    @dataclass
    class AxisEvent(GameControllerEvent):
        axis_id: int
        axis_value: float

    @dataclass
    class PovEvent(GameControllerEvent):
        pov_direction: int

    def __init__(self, index: int, polling_hz: int = 100):
        self.index = index
        self.event_queue = deque()

        if not pygame.get_init():
            pygame.init()

        # Initialize joystick module
        pygame.joystick.init()


        self.running = False
        self.connected = False
        self.polling_hz = polling_hz
        self._button_states = {}
        self._pov_state = -1
        self._axis_states = {}

        self._pov_callbacks: list[Callable[[int], Any]] = []
        self._button_callbacks: dict[int, list[Callable[[bool], Any]]] = {}

        self.on_disconnect: Callable[[], Any] | None = None

        # Pygame joystick object
        self._polling_thread = None
        self._event_thread = None

        self._joystick = pygame.joystick.Joystick(index)
        self._joystick.init()

        # Dead zone for analog sticks
        self.dead_zone = 0.1

        # D-pad state tracking
        self._dpad = {
            "up": False,
            "down": False,
            "left": False,
            "right": False,
        }

    def is_connected(self) -> bool:
        return self.connected and self._joystick is not None

    def get_button_state(self, button_id: int) -> bool:
        """Returns the state of a button (pressed: True, released: False)."""
        return self._button_states.get(button_id, False)

    def get_axis_value(self, axis_id: int, precision: int = 3) -> float:
        """Returns the current value of the specified axis (-1.0 to 1.0)."""
        value = self._axis_states.get(axis_id, 0.0)
        # Apply dead zone
        if abs(value) < self.dead_zone:
            value = 0.0
        return round(max(min(value, 1), -1), precision)

    def get_buttons(self) -> list[int]:
        """Returns a list of currently pressed buttons."""
        buttons = [key for key, value in self._button_states.items() if value]
        buttons.sort()
        return buttons

    def get_axes(self, precision: int = 3):
        return (
            {
                axis_id: self.get_axis_value(axis_id, precision)
                for axis_id in self._axis_states
            }
            if self._axis_states
            else {}
        )

    def get_pov_direction(self) -> int:
        """Returns the current POV (D-pad) direction."""
        return self._pov_state

    def register_button_callback(
        self, button_id: int, callback: Callable[[bool], Any]
    ) -> None:
        """Registers a callback for button events."""
        if button_id not in self._button_callbacks:
            self._button_callbacks[button_id] = []
        self._button_callbacks[button_id].append(callback)

    def register_pov_callback(self, callback: Callable[[int], Any]) -> None:
        """Registers a callback for POV events."""
        self._pov_callbacks.append(callback)

    def get_button_count(self):
        return self._joystick.get_numbuttons()

    def get_axis_count(self):
        return self._joystick.get_numaxes()

    def get_hat_count(self):
        return self._joystick.get_numhats()

    def _handle_disconnect(self):
        """Handles joystick disconnection."""
        print(f"Joystick {self.index} disconnected.")
        self.connected = False
        if self.on_disconnect:
            self.on_disconnect()

    def start_polling(self):
        """Starts the polling loop in separate threads."""
        if not self.running:
            self.running = True

    def stop(self):
        """Stops event handling and releases resources."""
        self.running = False

        if self._joystick and self._joystick.get_init():
            self._joystick.quit()

        # Wait for threads to finish
        if self._polling_thread and self._polling_thread.is_alive():
            self._polling_thread.join(timeout=1.0)
        if self._event_thread and self._event_thread.is_alive():
            self._event_thread.join(timeout=1.0)

        self.connected = False

class JoystickSender:
    def __init__(self, client: RedisCommClient, joystick: AbstractJoystickInterface, key: str) -> None:
        self.thread: threading.Thread | None = None
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
        self.thread: threading.Thread | None = None
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
        self._pov_callbacks: list[Callable[[int], Any]] = []
        self._axis_callbacks = {}

        # State tracking for callback triggering
        self._last_button_states = {}
        self._last_pov_state = -1
        self._last_axis_states = {}

        self.connected = False
        self.running = False

        # Start polling thread
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
        return button_id in sendable.value

    def get_axis_value(self, axis_id: int, precision: int = 3) -> float:
        sendable = self.client.get(f"{self._client_key}/axes", AnyListSendable)
        if not sendable:
            return 0.0
        return round(sendable.value[axis_id], precision) if axis_id < len(sendable.value) else 0.0

    def get_buttons(self) -> list[int | Enum | IntEnum]:
        sendable = self.client.get(f"{self._client_key}/buttons", AnyListSendable)
        if not sendable:
            return []
        return sendable.value

    def get_axes(self) -> list[float]:
        sendable = self.client.get(f"{self._client_key}/axes", AnyListSendable)
        if not sendable:
            return []
        return sendable.value

    def get_pov_direction(self) -> int:
        sendable = self.client.get(f"{self._client_key}/pov", IntegerSendable)
        if not sendable:
            return int
        return int(sendable.value)

    def register_button_callback(self, button_id: int | Enum | IntEnum, callback: Callable[[bool], Any]) -> None:
        """Registers a callback function for button press/release events."""
        self._button_callbacks[button_id] = callback

    def register_pov_callback(self, callback: Callable[[int], Any]) -> None:
        """Registers a callback function for POV (D-pad) direction changes."""
        self._pov_callbacks.append(callback)

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

                    if old_state != new_state and button in self._button_callbacks:
                        self._button_callbacks[button](new_state)

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
