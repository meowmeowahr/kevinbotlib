from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QTabWidget, QVBoxLayout, QWidget

from kevinbotlib.simulator.windowview import WindowView, register_window_view


class CameraPage(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        self.resolution = QLabel("Resolution: 640x480")
        self.layout.addWidget(self.resolution)

    def set_resolution(self, width: int, height: int):
        self.resolution.setText(f"Resolution: {width}x{height}")


@register_window_view("kevinbotlib.vision.cameras")
class CamerasWindowView(WindowView):
    new_tab = Signal(str)

    def __init__(self):
        super().__init__()
        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("CompactTabs")
        self.layout.addWidget(self.tabs)

        self.pages: dict[str, CameraPage] = {}
        self.new_tab.connect(self.create_tab)

    @property
    def title(self) -> str:
        return "Cameras"

    def generate(self) -> QWidget:
        return self.widget

    def create_tab(self, camera_name: str):
        if camera_name not in self.pages:
            page = CameraPage()
            self.tabs.addTab(page, camera_name)
            self.pages[camera_name] = page
        self.tabs.setCurrentWidget(self.pages[camera_name])

    def update(self, payload):
        if isinstance(payload, dict):
            match payload["type"]:
                case "new":
                    self.new_tab.emit(payload["name"])
                case "res":
                    self.pages[payload["name"]].set_resolution(*payload["res"])
