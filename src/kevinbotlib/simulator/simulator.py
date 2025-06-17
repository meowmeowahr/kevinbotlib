import multiprocessing
from collections.abc import Callable
from threading import Thread
from typing import TYPE_CHECKING, Any, TypeVar

from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
)

from kevinbotlib.comm.abstract import SetGetClientWithPubSub
from kevinbotlib.simulator._events import (
    _AddWindowEvent,
    _ExitSimulatorEvent,
    _SimulatorExitEvent,
    _SimulatorInputEvent,
    _WindowReadyEvent,
    _WindowViewPayloadEvent,
    _WindowViewUpdateEvent,
)
from kevinbotlib.simulator._gui import SimMainWindow
from kevinbotlib.simulator.windowview import WindowView, WindowViewOutputPayload
from kevinbotlib.util import socket_exists

if TYPE_CHECKING:
    from kevinbotlib.robot import BaseRobot

T = TypeVar("T", bound=WindowViewOutputPayload)


class SimulationFramework:
    """
    Robot Simulation Framework
    """

    def __init__(self, robot: "BaseRobot"):
        """
        Initialize the simulation framework.

        Args:
            robot: Robot to simulate
        """

        self.robot = robot

        self.sim_process: multiprocessing.Process | None = None
        self.event_watcher: multiprocessing.Process | None = None

        self.sim_in_queue: multiprocessing.Queue[_SimulatorInputEvent] = multiprocessing.Queue()
        self.sim_out_queue: multiprocessing.Queue[_SimulatorInputEvent] = multiprocessing.Queue()

        self._payload_callbacks: dict[
            type[WindowViewOutputPayload], list[Callable[[WindowViewOutputPayload], None]]
        ] = {}
        self._ready_callback: Callable[[], None] | None = None
        self._windows: list[str] = []

    @staticmethod
    def _simulator_bringup(
        port: int | None, host: str | None, in_queue: multiprocessing.Queue, out_queue: multiprocessing.Queue
    ):
        app = QApplication([])

        if port and host and not socket_exists(host, port, 5):
            QMessageBox.warning(
                None,
                "Redis Error",
                f"Expected a Redis Server at {host}:{port}, socket isn't available\nThe simulator will most likely not function properly.",
            )

        window = SimMainWindow(in_queue, out_queue)
        window.show()
        out_queue.put_nowait(_WindowReadyEvent())
        app.exec()

    def launch_simulator(
        self, comm_client: SetGetClientWithPubSub | None, ready_callback: Callable[[], None] | None = None
    ) -> None:
        """
        Start the simulator.

        Args:
            comm_client: Communication client used in simulations.
            ready_callback: Callback for when the simulator window is ready.
        """

        host = None
        port = None
        if comm_client:
            host = comm_client.host
            port = comm_client.port

        self._ready_callback = ready_callback

        self.sim_process = multiprocessing.Process(
            target=self._simulator_bringup, args=(port, host, self.sim_in_queue, self.sim_out_queue)
        )
        self.sim_process.name = "KevinbotLib.Simulator"
        self.sim_process.start()

        self.event_watcher = Thread(
            target=self._watch_events, daemon=True, name="KevinbotLib.SimFramework.SimulatorLifecycleOutputEventWatcher"
        )
        self.event_watcher.start()

    def exit_simulator(self) -> None:
        """
        Gracefully exit the simulator.
        """

        self.sim_in_queue.put_nowait(_ExitSimulatorEvent())

    def send_to_window(self, winid: str, payload: Any) -> None:
        """
        Send a payload to a WindowView

        Args:
            winid: WindowView ID
            payload: Payload to send.
        """

        self.sim_in_queue.put(_WindowViewUpdateEvent(winid, payload))

    def add_window(self, winid: str, window: type[WindowView]) -> None:
        """
        Add a new pre-registered WindowView to the simulator.

        Args:
            winid: WindowView ID. ID must be registered by the @register_window_view decorator.
            window: WindowView to add.
        """

        self.sim_in_queue.put(_AddWindowEvent(winid, window, default_open=True))
        self._windows.append(winid)

    @property
    def windows(self) -> list[str]:
        """
        Get the currently activated WindowView IDs.

        Returns:
            WindowView IDs.
        """

        return self._windows

    def add_payload_callback(self, payload_type: type[T], callback: Callable[[T], None]) -> None:
        """
        Add a new callback for a payload exiting a WindowView.

        Args:
            payload_type: Customized subclass type of WindowViewOutputPayload.
            callback: Callback function.
        """

        if payload_type in self._payload_callbacks:
            self._payload_callbacks[payload_type].append(callback)
        else:
            self._payload_callbacks[payload_type] = [callback]

    def _watch_events(self):
        while True:
            event = self.sim_out_queue.get()
            if isinstance(event, _SimulatorExitEvent):
                self.robot.telemetry.critical("The simulator has stopped")
                self.robot._signal_stop = True  # noqa: SLF001
            elif isinstance(event, _WindowReadyEvent):
                if self._ready_callback:
                    self._ready_callback()
            elif isinstance(event, _WindowViewPayloadEvent):
                if type(event.payload) in self._payload_callbacks:
                    for callback in self._payload_callbacks[type(event.payload)]:
                        callback(event.payload)
