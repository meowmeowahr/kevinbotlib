from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QImage, QColor, QPixmap
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

    # ! optional - define an icon for the WindowView
    # Icons must be PySide6 QIcon and scalable down to 16x16
    def icon(self, dark_mode: bool) -> QIcon:
        # this seems like a lot, but it just generates a red icon for use in this example
        image = QImage(QSize(16, 16), QImage.Format.Format_RGB888)
        image.fill(QColor(255, 0, 0))
        return QIcon(QPixmap.fromImage(image))

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
