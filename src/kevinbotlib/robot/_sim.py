import threading
import time
from typing import TYPE_CHECKING

import ansi2html
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from fonticon_mdi7.mdi7 import MDI7 as _MDI7

from kevinbotlib.apps import get_icon
from kevinbotlib.simulator import SimulationFramework
from kevinbotlib.simulator.windowview import (
    WindowView,
    WindowViewOutputPayload,
    register_window_view,
)

if TYPE_CHECKING:
    from kevinbotlib.robot import BaseRobot


def sim_telemetry_hook(winid: str, sim: SimulationFramework, message: str):
    sim.send_to_window(winid, message)


@register_window_view("kevinbotlib.robot.internal.telemetry")
class TelemetryWindowView(WindowView):
    add_line = Signal(str)

    def __init__(self):
        super().__init__()
        self.telemetry = QTextEdit()
        self.telemetry.setReadOnly(True)
        self.telemetry.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.telemetry.document().setMaximumBlockCount(1000)
        self.telemetry.setStyleSheet("border: none;")
        self.add_line.connect(self.append_ansi)

        self.ansi_convertor = ansi2html.Ansi2HTMLConverter()

    @property
    def title(self):
        return "Telemetry"

    def icon(self, dark_mode: bool) -> QIcon:
        return get_icon(_MDI7.text)

    def generate(self) -> QWidget:
        return self.telemetry

    def update(self, payload):
        """Accept `str | Iterable[str]` and append to the log."""
        if isinstance(payload, str):
            self.add_line.emit(payload)
        else:
            for line in payload:
                self.add_line.emit(str(line))

    def append_ansi(self, ansi: str):
        self.telemetry.append(self.ansi_convertor.convert(ansi.strip("\n\r")))


@register_window_view("kevinbotlib.robot.internal.metrics")
class MetricsWindowView(WindowView):
    set = Signal(str, float)

    def __init__(self):
        super().__init__()
        from PySide6.QtCore import QTimer

        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)

        self.metrics = QTextEdit()
        self.metrics.setReadOnly(True)
        self.metrics.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.metrics.setStyleSheet("border: none; font-family: monospace;")
        self.layout.addWidget(self.metrics)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setFixedHeight(20)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        self.layout.addWidget(self.progress)

        self.set.connect(self.set_text)

        self._interval = 1.0
        self._elapsed = 0.0

        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._on_timer)
        self.timer.start()

    @property
    def title(self):
        return "Metrics"

    def icon(self, dark_mode: bool) -> QIcon:
        return get_icon(_MDI7.speedometer)

    def generate(self) -> QWidget:
        return self.widget

    def set_text(self, payload, interval=None):
        self.metrics.setPlainText(payload)
        if interval is not None:
            self._interval = interval
            self._elapsed = 0.0
            self.progress.setValue(0)
        self.progress.setVisible(True)

    def update(self, payload):
        """Accept `str | Iterable[str]` and append to the log."""
        if isinstance(payload, dict):
            self.set.emit(payload["metrics"], payload["interval"])

    def _on_timer(self):
        self._elapsed += self.timer.interval() / 1000.0
        percent = min(int((self._elapsed / self._interval) * 100), 100)
        self.progress.setValue(percent)
        if self._elapsed >= self._interval:
            self._elapsed = 0.0


@register_window_view("kevinbotlib.robot.internal.proc")
class ProcInfoWindowView(WindowView):
    set_process_time = Signal(str)
    set_cycles = Signal(str)

    def __init__(self):
        super().__init__()

        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)

        self.process_time = QLabel("Process Time: ????.????")
        self.process_time.setFont(QFont("monospace"))
        self.process_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.process_time)
        self.set_process_time.connect(self.update_process_time)

        self.cps = QLabel("Cycles/Second: ???.??")
        self.cps.setFont(QFont("monospace"))
        self.cps.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.cps)
        self.set_cycles.connect(self.update_cycles)

    @property
    def title(self):
        return "Process Info"

    def icon(self, dark_mode: bool) -> QIcon:
        return get_icon(_MDI7.information)

    def generate(self) -> QWidget:
        return self.widget

    def update(self, payload):
        if isinstance(payload, dict):
            match payload["type"]:
                case "time":
                    self.set_process_time.emit(payload["proc_time"])
                case "cps":
                    self.set_cycles.emit(payload["cps"])

    def update_process_time(self, time: str):
        self.process_time.setText(f"Process Time: {time}")

    def update_cycles(self, cycles: str):
        self.cps.setText(f"Cycles/Second: {cycles}")


class StateButtonsEventPayload(WindowViewOutputPayload):
    def __init__(self, payload: str):
        self._payload = payload

    def payload(self) -> str:
        return self._payload


class OpModeEventPayload(WindowViewOutputPayload):
    def __init__(self, payload: str):
        self._payload = payload

    def payload(self) -> str:
        return self._payload


@register_window_view("kevinbotlib.robot.internal.state_buttons")
class StateButtonsView(WindowView):
    set_opmodes = Signal(list)
    set_opmode = Signal(str)
    set_state = Signal(bool)

    def __init__(self):
        super().__init__()

        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)

        self.main_layout = QHBoxLayout()
        self.layout.addLayout(self.main_layout)

        self.enable_button = QPushButton("Enable")
        self.enable_button.clicked.connect(self.enable)
        self.main_layout.addWidget(self.enable_button)

        self.disable_button = QPushButton("Disable")
        self.disable_button.clicked.connect(self.disable)
        self.main_layout.addWidget(self.disable_button)

        self.estop_button = QPushButton("E-Stop")
        self.estop_button.clicked.connect(self.estop)
        self.layout.addWidget(self.estop_button)

        self.opmodes_selector = QListWidget()
        self.opmodes_selector.currentTextChanged.connect(self.opmode_changed)
        self.layout.addWidget(self.opmodes_selector)

        self.enabled_text = QLabel("Enabled: ????")
        self.enabled_text.setFont(QFont("monospace"))
        self.layout.addWidget(self.enabled_text)

        self.opmode_text = QLabel("OpMode: ????")
        self.opmode_text.setFont(QFont("monospace"))
        self.layout.addWidget(self.opmode_text)

        self.set_opmodes.connect(self.update_opmodes)
        self.set_opmode.connect(self.update_opmode)
        self.set_state.connect(self.update_state)

    @property
    def title(self):
        return "Robot State"

    def icon(self, dark_mode: bool) -> QIcon:
        return get_icon(_MDI7.gesture_tap_button)

    def generate(self) -> QWidget:
        return self.widget

    def enable(self):
        self.send_payload(StateButtonsEventPayload("enable"))

    def disable(self):
        self.send_payload(StateButtonsEventPayload("disable"))

    def estop(self):
        self.send_payload(StateButtonsEventPayload("estop"))

    def update_opmodes(self, opmodes: list[str]):
        self.opmodes_selector.addItems(opmodes)

    def update_opmode(self, opmode: str):
        self.opmodes_selector.blockSignals(True)
        index = self.opmodes_selector.findItems(opmode, Qt.MatchFlag.MatchExactly)
        if index:
            self.opmodes_selector.setCurrentRow(self.opmodes_selector.row(index[0]))
        self.opmodes_selector.blockSignals(False)
        self.opmode_text.setText(f"OpMode: {opmode}")

    def update_state(self, enabled: bool):
        self.enabled_text.setText(f"Enabled: {enabled}")

    def opmode_changed(self, opmode: str):
        self.send_payload(OpModeEventPayload(opmode))

    def update(self, payload: dict):
        if payload["type"] == "opmodes":
            self.set_opmodes.emit(payload["opmodes"])
        if payload["type"] == "opmode":
            self.set_opmode.emit(payload["opmode"])
        if payload["type"] == "state":
            self.set_state.emit(payload["enabled"])


def make_simulator(robot: "BaseRobot") -> SimulationFramework:
    simulator = SimulationFramework(robot)

    # noinspection PyProtectedMember
    def sim_ready():
        simulator.send_to_window(
            "kevinbotlib.robot.internal.state_buttons",
            {"type": "opmodes", "opmodes": robot._opmodes},  # noqa: SLF001
        )
        simulator.send_to_window(
            "kevinbotlib.robot.internal.state_buttons",
            {"type": "opmode", "opmode": robot._opmode},  # noqa: SLF001
        )

    simulator.launch_simulator(robot.comm_client, sim_ready)
    robot.estop_hooks.append(simulator.exit_simulator)
    robot.telemetry.trace("Launched simulator")

    simulator.add_window("kevinbotlib.robot.internal.telemetry", TelemetryWindowView)
    robot.telemetry.trace("Added Telemetry simulator WindowView")

    simulator.add_window("kevinbotlib.robot.internal.proc", ProcInfoWindowView)
    robot.telemetry.trace("Added Time simulator WindowView")

    simulator.add_window("kevinbotlib.robot.internal.state_buttons", StateButtonsView)
    robot.telemetry.trace("Added State Buttons simulator WindowView")

    simulator.add_window("kevinbotlib.robot.internal.metrics", MetricsWindowView)
    robot.telemetry.trace("Added Metrics simulator WindowView")

    # telemetry updates
    robot.telemetry.add_hook_ansi(lambda *x: sim_telemetry_hook("kevinbotlib.robot.internal.telemetry", simulator, *x))

    # time updates
    def time_updater():
        start = time.monotonic()
        while True:
            simulator.send_to_window(
                "kevinbotlib.robot.internal.proc", {"type": "time", "proc_time": f"{time.monotonic()-start:0>9.4f}"}
            )
            simulator.send_to_window("kevinbotlib.robot.internal.proc", {"type": "cps", "cps": str(robot.current_cps)})
            time.sleep(0.05)

    threading.Thread(target=time_updater, daemon=True, name="KevinbotLib.Simulator.LiveWindows.Time.Update").start()

    # state updates
    def sim_state_callback(payload: StateButtonsEventPayload):
        match payload.payload():
            case "enable":
                robot.enabled = True
            case "disable":
                robot.enabled = False
            case "estop":
                robot.estop()

    simulator.add_payload_callback(StateButtonsEventPayload, sim_state_callback)

    # opmode updates
    def opmode_change_callback(payload: OpModeEventPayload):
        robot.opmode = payload.payload()

    simulator.add_payload_callback(OpModeEventPayload, opmode_change_callback)
    return simulator
