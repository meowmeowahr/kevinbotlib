import ansi2html
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from kevinbotlib.simulator import SimulationFramework
from kevinbotlib.simulator.windowview import (
    WindowView,
    WindowViewOutputPayload,
    register_window_view,
)


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


@register_window_view("kevinbotlib.robot.internal.time")
class TimeWindowView(WindowView):
    set_process_time = Signal(str)

    def __init__(self):
        super().__init__()

        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)

        self.process_time = QLabel("Process Time: ????.????")
        self.process_time.setFont(QFont("monospace"))
        self.process_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.process_time)
        self.set_process_time.connect(self.update_process_time)

    @property
    def title(self):
        return "Process Time"

    def generate(self) -> QWidget:
        return self.widget

    def update(self, payload):
        if isinstance(payload, str):
            self.set_process_time.emit(payload)

    def update_process_time(self, time: str):
        self.process_time.setText(f"Process Time: {time}")


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
        self.set_opmodes.connect(self.update_opmodes)
        self.set_opmode.connect(self.update_opmode)

    @property
    def title(self):
        return "Robot State"

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

    def opmode_changed(self, opmode: str):
        self.send_payload(OpModeEventPayload(opmode))

    def update(self, payload: dict):
        if payload["type"] == "opmodes":
            self.set_opmodes.emit(payload["opmodes"])
        if payload["type"] == "opmode":
            self.set_opmode.emit(payload["opmode"])
