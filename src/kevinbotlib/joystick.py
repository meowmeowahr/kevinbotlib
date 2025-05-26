import multiprocessing
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Any, final

import sdl2
import sdl2.ext

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

sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_GAMECONTROLLER)


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


class JoystickButton(IntEnum):
    A = sdl2.SDL_CONTROLLER_BUTTON_A
    B = sdl2.SDL_CONTROLLER_BUTTON_B
    X = sdl2.SDL_CONTROLLER_BUTTON_X
    Y = sdl2.SDL_CONTROLLER_BUTTON_Y
    LEFT_STICK = sdl2.SDL_CONTROLLER_BUTTON_LEFTSTICK
    RIGHT_STICK = sdl2.SDL_CONTROLLER_BUTTON_RIGHTSTICK
    LEFT_BUMPER = sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER
    RIGHT_BUMPER = sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER
    START = sdl2.SDL_CONTROLLER_BUTTON_START
    BACK = sdl2.SDL_CONTROLLER_BUTTON_BACK
    GUIDE = sdl2.SDL_CONTROLLER_BUTTON_GUIDE


class RawLocalJoystickDevice(AbstractJoystickInterface):
    """Gamepad-agnostic polling and event-based joystick input with disconnect detection."""

    class ButtonSignal(IntEnum):
        Pressed = 1
        Released = 2

    @dataclass
    class GameControllerEvent:
        identifier: int
        timestamp: int

    @dataclass
    class ButtonEvent(GameControllerEvent):
        button_id: JoystickButton
        button_signal: "RawLocalJoystickDevice.ButtonSignal"

    @dataclass
    class AxisEvent(GameControllerEvent):
        axis_id: int
        axis_value: float

    def __init__(self, index: int, polling_hz: int = 100):
        super().__init__()
        self.index = index
        self.event_queue = multiprocessing.Queue()
        self._logging_queue = multiprocessing.Queue()

        self._logger = _Logger()

        self.running = False
        self.connected = False
        self.polling_hz = polling_hz
        self._button_states = {}
        self._pov_state = -1
        self._axis_states = {}

        self.on_disconnect: Callable[[], Any] | None = None

    def is_connected(self) -> bool:
        return self.connected

    def get_button_count(self) -> int:
        """Returns the total number of buttons on the joystick."""
        if not self._sdl_joystick or not sdl2.SDL_JoystickGetAttached(self._sdl_joystick):
            return 0
        return sdl2.SDL_JoystickNumButtons(self._sdl_joystick)

    def get_button_state(self, button_id: int) -> bool:
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
        return (
            {
                axis_id: round(float(max(min(self._axis_states[axis_id], 1), -1)), precision)
                for axis_id in self._axis_states
            }
            if self._axis_states
            else {}
        )

    def get_pov_direction(self) -> int:
        """Returns the current POV (D-pad) direction."""
        return self._pov_state

    def _log_catcher(self):
        while self.running:
            entry = self._logging_queue.get()
            self._logger.log(*entry)

    def _event_catcher(self):
        while self.running:
            entry = self.event_queue.get()
            if isinstance(entry, RawLocalJoystickDevice.AxisEvent):
                self._axis_states[entry.axis_id] = entry.axis_value
            elif isinstance(entry, RawLocalJoystickDevice.ButtonEvent):
                if entry.button_signal == RawLocalJoystickDevice.ButtonSignal.Pressed:
                    self._button_states[entry.button_id] = True
                else:
                    self._button_states[entry.button_id] = False

    @staticmethod
    def _event_loop(index: int, polling_hz: int, logger: multiprocessing.Queue, evq: multiprocessing.Queue) -> None:
        """Internal loop for processing SDL events synchronously. Must run in its own process or MainThread"""
        if sdl2.SDL_IsGameController(index):
            _sdl_joystick = sdl2.SDL_GameControllerOpen(index)
            if _sdl_joystick:
                name = sdl2.SDL_GameControllerName(_sdl_joystick)
                logger.put_nowait((Level.DEBUG, f"Opened controller {index}: {name.decode() if name else 'Unknown'}"))
            else:
                logger.put_nowait((Level.ERROR, f"Failed to open controller {index}"))
        else:
            raise JoystickMissingException(index)

        running = True
        event = sdl2.SDL_Event()

        while running:
            while sdl2.SDL_PollEvent(event):
                if event.type == sdl2.SDL_QUIT:
                    logger.put_nowait((Level.WARNING, "Unexpected SQL_QUIT event"))

                elif event.type == sdl2.SDL_CONTROLLERBUTTONDOWN:
                    if sdl2.SDL_GameControllerGetPlayerIndex(_sdl_joystick) != index:
                        continue
                    button = event.cbutton.button
                    logger.put_nowait((Level.TRACE, f"Button pressed: {button} on controller {event.cbutton.which}"))
                    evq.put_nowait(
                        RawLocalJoystickDevice.ButtonEvent(
                            identifier=event.cbutton.which,
                            timestamp=event.cbutton.timestamp,
                            button_id=JoystickButton(button),
                            button_signal=RawLocalJoystickDevice.ButtonSignal.Pressed,
                        )
                    )

                elif event.type == sdl2.SDL_CONTROLLERBUTTONUP:
                    if sdl2.SDL_GameControllerGetPlayerIndex(_sdl_joystick) != index:
                        continue
                    button = event.cbutton.button
                    logger.put_nowait((Level.TRACE, f"Button released: {button} on controller {event.cbutton.which}"))
                    evq.put_nowait(
                        RawLocalJoystickDevice.ButtonEvent(
                            identifier=event.cbutton.which,
                            timestamp=event.cbutton.timestamp,
                            button_id=JoystickButton(button),
                            button_signal=RawLocalJoystickDevice.ButtonSignal.Released,
                        )
                    )

                elif event.type == sdl2.SDL_CONTROLLERAXISMOTION:
                    if sdl2.SDL_GameControllerGetPlayerIndex(_sdl_joystick) != index:
                        continue

                    axis = event.caxis.axis
                    value = event.caxis.value

                    # Normalize axis values (-32768 to 32767) to -1.0 to 1.0
                    normalized_value = value / 32767.0
                    logger.put_nowait(
                        (Level.TRACE, f"{axis}: {normalized_value:.2f} on controller {event.cbutton.which}")
                    )
                    evq.put_nowait(
                        RawLocalJoystickDevice.AxisEvent(
                            identifier=event.caxis.which,
                            timestamp=event.caxis.timestamp,
                            axis_id=axis,
                            axis_value=normalized_value,
                        )
                    )

                elif event.type == sdl2.SDL_CONTROLLERDEVICEADDED:
                    device_index = event.cdevice.which
                    if sdl2.SDL_IsGameController(device_index) and device_index == index:
                        _sdl_joystick = sdl2.SDL_GameControllerOpen(device_index)
                        logger.put_nowait((Level.INFO, f"Re-initialized current controller {device_index}"))
                    logger.put_nowait((Level.DEBUG, f"Controller connected: {device_index}"))

                elif event.type == sdl2.SDL_CONTROLLERDEVICEREMOVED:
                    logger.put_nowait((Level.DEBUG, "Controller disconnected"))

            time.sleep(1 / polling_hz)

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
            multiprocessing.Process()
            SafeTelemeterizedProcess(
                target=self._event_loop,
                daemon=True,
                name=f"KevinbotLib.Joystick.EvProcess.{self.index}",
                args=(self.index, self.polling_hz, self._logging_queue, self.event_queue),
            ).start()
            threading.Thread(
                target=self._log_catcher,
                daemon=True,
                name=f"KevinbotLib.Joystick.LogRedirector.{self.index}",
            ).start()
            threading.Thread(
                target=self._event_catcher,
                daemon=True,
                name=f"KevinbotLib.Joystick.EvCatcher.{self.index}",
            ).start()

    def stop(self):
        """Stops event handling and releases resources."""
        self.running = False
        sdl2.SDL_GameControllerClose(self._sdl_joystick)


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
