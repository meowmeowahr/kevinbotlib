from typing import Any

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from kevinbotlib.robot import BaseRobot
from kevinbotlib.simulator.windowview import WindowView, WindowViewOutputPayload, register_window_view


class ResetPayload(WindowViewOutputPayload):
    def payload(self) -> Any:
        return "reset"


@register_window_view("test.mywindowview")
class MyWindowView(WindowView):
    def __init__(self):
        super().__init__()

        self.widget = QWidget()

        self.layout = QVBoxLayout()
        self.widget.setLayout(self.layout)

        self.label = QLabel("Robot Cycles: ?")
        self.layout.addWidget(self.label)

        self.button = QPushButton("Reset")
        self.button.clicked.connect(lambda: self.send_payload(ResetPayload()))
        self.layout.addWidget(self.button)

    @property
    def title(self):
        return "My Awesome WindowView"

    def generate(self) -> QWidget:
        return self.widget

    def update(self, payload: Any) -> None:
        self.label.setText(f"Robot Cycles: {payload}")


class DemoRobot(BaseRobot):
    def __init__(self):
        super().__init__(
            ["Test"],
            enable_stderr_logger=True,
        )

        self.cycles = 0
        if BaseRobot.IS_SIM:
            self.simulator.add_window("test.mywindowview", MyWindowView)

            def reset_cycles(payload: WindowViewOutputPayload):
                if payload.payload() == "reset":
                    self.cycles = 0

            self.simulator.add_payload_callback(ResetPayload, reset_cycles)

    def robot_periodic(self, opmode: str, enabled: bool):
        super().robot_periodic(opmode, enabled)

        self.cycles += 1
        self.simulator.send_to_window("test.mywindowview", self.cycles)


if __name__ == "__main__":
    DemoRobot().run()
