import sys

from cv2_enumerate_cameras import enumerate_cameras, supported_backends

from PySide6.QtCore import Signal, QTimer, QSize, QEvent, Qt, QThread
from PySide6.QtGui import QPixmap, QResizeEvent, QColor, QPainter, QFont
from PySide6.QtWidgets import (
    QLabel,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QFormLayout,
    QComboBox,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QMessageBox,
)
from fonticon_mdi7 import MDI7

from kevinbotlib.simulator.windowview import WindowView, register_window_view
from kevinbotlib.apps import get_icon as icon


class FrameTimerThread(QThread):
    def __init__(self, callback, interval_ms=33, parent=None):
        super().__init__(parent)
        self.callback = callback
        self.interval_ms = interval_ms
        self._running = True

    def run(self):
        while self._running:
            self.callback()
            self.msleep(self.interval_ms)

    def stop(self):
        self._running = False

class CameraPage(QWidget):
    def __init__(self):
        super().__init__()
        self.root_layout = QVBoxLayout(self)

        self.form = QFormLayout(self)
        self.root_layout.addLayout(self.form)

        self.resolution = QLabel("Resolution: ????x????")
        self.form.addRow(self.resolution)

        self.fps = QLabel("FPS: ??")
        self.form.addRow(self.fps)

        self.source_layout = QHBoxLayout()
        self.source_layout.setContentsMargins(0, 0, 0, 0)
        self.form.addRow("Video Source", self.source_layout)

        self.source = QComboBox()
        self.source.addItem("Uploaded Image")
        self.source_layout.addWidget(self.source)

        self.source_refresh = QPushButton()
        self.source_refresh.setIconSize(QSize(18, 18))
        self.source_refresh.setIcon(icon(MDI7.refresh))
        self.source_refresh.setFixedSize(QSize(32, 32))
        self.source_refresh.clicked.connect(self.refresh_video_sources)
        self.source_layout.addWidget(self.source_refresh)

        self.image = QLabel()
        self.image.setScaledContents(False)
        self.image.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.root_layout.addWidget(self.image, 2)

        self.frame = QPixmap(QSize(640, 480))
        self.frame.fill(Qt.GlobalColor.darkRed)
        self.image.setPixmap(self.frame)

        painter = QPainter(self.frame)
        painter.setPen(QColor("white"))
        font = QFont()
        font.setPointSize(60)
        font.setBold(True)
        painter.setFont(font)
        rect = self.frame.rect()
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No Image")
        painter.end()

        self.frame_timer_thread = FrameTimerThread(self.update_frame, 1000 // 30, self)
        self.frame_timer_thread.start()

        self.refresh_video_sources()

    def set_resolution(self, width: int, height: int):
        self.resolution.setText(f"Resolution: {width}x{height}")

    def set_fps(self, fps: float):
        self.fps.setText(f"FPS: {fps:.2f}")
        self.frame_timer_thread.interval_ms = int(1000 / fps)

    def refresh_video_sources(self):
        current = self.source.currentText()
        self.source.clear()
        self.source.addItem("Uploaded Image")

        if not sys.platform == "darwin":
            cameras = enumerate_cameras()
            cameras.sort(key=lambda x: x.index)
            for camera in reversed(cameras):
                # remove duplicated
                if camera.name not in [self.source.itemText(i) for i in range(self.source.count())]:
                    self.source.addItem(camera.name, camera.index)
        else:
            QMessageBox.warning(self, "Platform Support", "Camera passthrough currently does not support macOS.")

        if current in [self.source.itemText(i) for i in range(self.source.count())]:
            self.source.setCurrentText(current)

    def update_scaled_pixmap(self):
        if not self.frame.isNull():
            scaled = self.frame.scaled(
                self.image.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image.setPixmap(scaled)

    def resizeEvent(self, event: QResizeEvent):
        self.update_scaled_pixmap()
        super().resizeEvent(event)

    def update_frame(self):
        print(self.source.currentText())

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
                case "fps":
                    self.pages[payload["name"]].set_fps(payload["fps"])
