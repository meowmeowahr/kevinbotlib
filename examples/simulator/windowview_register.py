from PySide6.QtWidgets import QLabel, QWidget

from kevinbotlib.robot import BaseRobot
from kevinbotlib.simulator.windowview import WindowView, register_window_view


@register_window_view("test.mywindowview")
class MyWindowView(WindowView):
    def __init__(self):
        super().__init__()

    @property
    def title(self):
        return "My Awesome WindowView"

    def generate(self) -> QWidget:
        return QLabel("Hello World!")


class DemoRobot(BaseRobot):
    def __init__(self):
        super().__init__(
            ["Test"],
            enable_stderr_logger=True,
        )

        if BaseRobot.IS_SIM:
            self.simulator.add_window("test.mywindowview", MyWindowView)
            self.telemetry.info(f"Registered WindowViews: {self.simulator.windows}")


if __name__ == "__main__":
    DemoRobot().run()
