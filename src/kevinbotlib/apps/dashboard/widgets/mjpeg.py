from typing import TYPE_CHECKING

import pybase64
from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGraphicsProxyWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from kevinbotlib.apps.common.settings_rows import Divider
from kevinbotlib.apps.dashboard.widgets.base import WidgetItem
from kevinbotlib.comm import RedisCommClient
from kevinbotlib.logger import Logger

if TYPE_CHECKING:
    from kevinbotlib.apps.dashboard.app import GridGraphicsView


class FrameDecodeWorker(QObject):
    finished = Signal(QPixmap)
    error = Signal(str)

    @Slot(str, int, int)
    def process(self, base64_data: str, width: int, height: int):
        try:
            decoded = pybase64.b64decode(base64_data)
            image = QImage.fromData(decoded, "JPG")  # type: ignore
            if image.isNull():
                return

            scaled = image.scaled(
                width,
                height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
            pixmap = QPixmap.fromImage(scaled)
            self.finished.emit(pixmap)
        except ValueError as e:
            self.error.emit(str(e))


class MjpegCameraStreamWidgetSettings(QDialog):
    options_changed = Signal(dict)

    def __init__(self, options: dict | None = None, parent=None):
        super().__init__(parent)
        if not options:
            options = {}
        self.options = options

        self.setWindowTitle("Camera Stream Settings")
        self.setModal(True)

        self.root_layout = QVBoxLayout()
        self.setLayout(self.root_layout)

        self.form = QFormLayout()
        self.root_layout.addLayout(self.form)

        self.form.addRow(Divider("Frame Rate"))

        self.fps = QSpinBox(minimum=1, maximum=20, value=self.options.get("fps", 15))
        self.fps.valueChanged.connect(self.set_fps)
        self.form.addRow("FPS", self.fps)

        self.button_layout = QHBoxLayout()
        self.button_layout.addStretch()
        self.root_layout.addLayout(self.button_layout)

        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply)
        self.button_layout.addWidget(self.apply_button)

        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.close)
        self.button_layout.addWidget(self.exit_button)

    def set_fps(self, value: int):
        self.options["fps"] = value

    def apply(self):
        self.options_changed.emit(self.options)


class MjpegCameraStreamWidgetItem(WidgetItem):
    def __init__(
        self,
        title: str,
        key: str,
        options: dict,
        grid: "GridGraphicsView",
        span_x=1,
        span_y=1,
        _client: RedisCommClient | None = None,
    ):
        super().__init__(title, key, options, grid, span_x, span_y)
        self.label_rect = None
        self.kind = "cameramjpeg"

        self.settings = MjpegCameraStreamWidgetSettings(self.options, grid)
        self.settings.options_changed.connect(self.options_changed)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("background: black;")

        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(self.label)

        self.pending_data = None
        self.update_label_geometry()

        # Throttle fps
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self._apply_pending_frame)
        self.frame_timer.start(1000 // options.get("fps", 15))

        # Set up a worker thread
        self.worker_thread = QThread(self)
        self.worker_thread.setObjectName("MjpegWorker")
        self.worker = FrameDecodeWorker()
        self.worker.moveToThread(self.worker_thread)
        self.worker.finished.connect(self._on_frame_ready)
        self.worker.error.connect(self._on_worker_error)
        self.worker_thread.start()

    def options_changed(self, options: dict):
        self.options = options
        self.frame_timer.setInterval(1000 // options.get("fps", 15))

    def update_label_geometry(self):
        label_margin = self.margin + 30  # Leave room for title
        self.label_rect = (
            self.margin,
            label_margin,
            self.width - 2 * self.margin,
            self.height - label_margin - self.margin,
        )
        self.proxy.setGeometry(*self.label_rect)

    def set_span(self, x, y):
        super().set_span(x, y)
        self.update_label_geometry()

    def prepareGeometryChange(self):  # noqa: N802
        super().prepareGeometryChange()
        self.update_label_geometry()

    def update_data(self, data: dict):
        super().update_data(data)
        self.pending_data = data  # Throttled display

    def _apply_pending_frame(self):
        if not self.pending_data:
            return

        base64_data = self.pending_data.get("value", "")
        width = self.label_rect[2]
        height = self.label_rect[3]
        self.pending_data = None
        QTimer.singleShot(0, lambda: self.worker.process(base64_data, width, height))

    @Slot(QPixmap)
    def _on_frame_ready(self, pixmap: QPixmap):
        self.label.setPixmap(pixmap)

    @Slot(str)
    def _on_worker_error(self, error: str):
        Logger().error(f"Error processing video stream: {error}")

    def create_context_menu(self):
        menu = super().create_context_menu()

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.settings.show)
        menu.addAction(settings_action)

        return menu

    def close(self):
        self.worker_thread.quit()
        self.worker_thread.wait()
        self.worker.deleteLater()
        self.worker_thread.deleteLater()
        super().close()
