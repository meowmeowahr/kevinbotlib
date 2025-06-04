import ansi2html
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QTextEdit, QWidget, QVBoxLayout, QLabel

from kevinbotlib.simulator import SimulationFramework
from kevinbotlib.simulator.windowview import WindowView, register_window_view


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
