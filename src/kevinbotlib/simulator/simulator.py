import multiprocessing
from collections.abc import Callable
from threading import Thread
from typing import TYPE_CHECKING, Any, TypeVar

from PySide6.QtWidgets import (
    QApplication,
)

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

if TYPE_CHECKING:
    from kevinbotlib.robot import BaseRobot

T = TypeVar("T", bound=WindowViewOutputPayload)


class SimulationFramework:
    def __init__(self, robot: "BaseRobot"):
        self.robot = robot

        self.sim_process: multiprocessing.Process | None = None
        self.event_watcher: multiprocessing.Process | None = None

        self.sim_in_queue: multiprocessing.Queue[_SimulatorInputEvent] = multiprocessing.Queue()
        self.sim_out_queue: multiprocessing.Queue[_SimulatorInputEvent] = multiprocessing.Queue()

        self._payload_callbacks: dict[
            type[WindowViewOutputPayload], list[Callable[[WindowViewOutputPayload], None]]
        ] = {}
        self._ready_callback: Callable[[], None] | None = None

    @staticmethod
    def simulator_run(in_queue: multiprocessing.Queue, out_queue: multiprocessing.Queue):
        app = QApplication([])
        window = SimMainWindow(in_queue, out_queue)
        window.show()
        out_queue.put_nowait(_WindowReadyEvent())
        app.exec()

    def launch_simulator(self, ready_callback: Callable[[], None] | None = None):
        self._ready_callback = ready_callback

        self.sim_process = multiprocessing.Process(
            target=self.simulator_run, args=(self.sim_in_queue, self.sim_out_queue)
        )
        self.sim_process.name = "KevinbotLib.Simulator"
        self.sim_process.start()

        self.event_watcher = Thread(
            target=self._watch_events, daemon=True, name="KevinbotLib.SimFramework.SimulatorLifecycleOutputEventWatcher"
        )
        self.event_watcher.start()

    def exit_simulator(self):
        self.sim_in_queue.put_nowait(_ExitSimulatorEvent())

    def send_to_window(self, winid: str, payload: Any):
        self.sim_in_queue.put(_WindowViewUpdateEvent(winid, payload))

    def add_window(self, name: str, window: type[WindowView]):
        self.sim_in_queue.put(_AddWindowEvent(name, window, default_open=True))

    def add_payload_callback(self, payload_type: type[T], callback: Callable[[T], None]):
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
