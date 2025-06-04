import multiprocessing
from threading import Thread
from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import (
    QApplication,
)

from kevinbotlib.simulator._events import (
    _AddWindowEvent,
    _SimulatorInputEvent,
    _WindowViewUpdateEvent,
)
from kevinbotlib.simulator._gui import SimMainWindow
from kevinbotlib.simulator.windowview import WindowView

if TYPE_CHECKING:
    from kevinbotlib.robot import BaseRobot


class SimulationFramework:
    def __init__(self, robot: "BaseRobot"):
        self.robot = robot

        self.sim_process: multiprocessing.Process | None = None
        self.event_watcher: multiprocessing.Process | None = None

        self.sim_in_queue: multiprocessing.Queue[_SimulatorInputEvent] = multiprocessing.Queue()
        self.sim_out_queue: multiprocessing.Queue[_SimulatorInputEvent] = multiprocessing.Queue()

    @staticmethod
    def simulator_run(in_queue: multiprocessing.Queue, out_queue: multiprocessing.Queue):
        app = QApplication([])
        window = SimMainWindow(in_queue, out_queue)
        window.show()
        app.exec()

    def launch_simulator(self):
        self.sim_process = multiprocessing.Process(
            target=self.simulator_run, args=(self.sim_in_queue, self.sim_out_queue)
        )
        self.sim_process.name = "KevinbotLib.Simulator"
        self.sim_process.start()

        self.event_watcher = Thread(
            target=self._watch_events, daemon=True, name="KevinbotLib.SimFramework.SimulatorLifecycleOutputEventWatcher"
        )
        self.event_watcher.start()

    def send_to_window(self, winid: str, payload: Any):
        self.sim_in_queue.put(_WindowViewUpdateEvent(winid, payload))

    def add_window(self, name: str, window: type[WindowView]):
        self.sim_in_queue.put(_AddWindowEvent(name, window, default_open=True))

    def _watch_events(self):
        while True:
            event = self.sim_out_queue.get()

            match type(event):
                case _SimulatorExitEvent:
                    self.robot.telemetry.critical("The simulator has stopped")
                    self.robot._signal_stop = True  # noqa: SLF001
