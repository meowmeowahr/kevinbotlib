import re
import sys
from collections.abc import Callable
from multiprocessing import current_process
from typing import ClassVar

import cv2
import numpy as np
import zmq
from cv2_enumerate_cameras import enumerate_cameras
from fonticon_mdi7 import MDI7
from fonticon_mdi7.mdi7 import MDI7 as _MDI7
from PySide6.QtCore import QMutex, QSize, Qt, QThread, Signal, Slot
from PySide6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from kevinbotlib.apps import get_icon as icon
from kevinbotlib.logger import Logger
from kevinbotlib.simulator.windowview import WindowView, register_window_view


class FrameTimerThread(QThread):
    _frame_timer_mutex: ClassVar[QMutex] = QMutex()

    def __init__(self, callback, interval_ms=33, parent=None):
        super().__init__(parent)
        self.callback = callback
        self.interval_ms = interval_ms
        self._running = True

    def run(self):
        while self._running:
            FrameTimerThread._frame_timer_mutex.lock()
            self.callback()
            FrameTimerThread._frame_timer_mutex.unlock()
            self.msleep(self.interval_ms)

    def stop(self):
        self._running = False


class ImageEditor(QDialog):
    def __init__(self, original_pixmap: QPixmap, target_size: QSize, parent=None):
        super().__init__(parent)
        self.original_pixmap = original_pixmap
        self.target_size = target_size
        self.edited_pixmap = original_pixmap

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.setModal(False)
        self.setMinimumWidth(280)
        self.setWindowTitle("Editor")

        # Preview label
        self.preview = QLabel()
        self.preview.setScaledContents(False)
        self.preview.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.preview)

        # Edit mode selection
        self.mode_layout = QHBoxLayout()
        self.layout.addLayout(self.mode_layout)

        self.mode_label = QLabel("Edit Mode:")
        self.mode_layout.addWidget(self.mode_label)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Center", "Stretch", "Fit"])
        self.mode_combo.currentTextChanged.connect(self.update_image)
        self.mode_layout.addWidget(self.mode_combo)

        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.accept)
        self.layout.addWidget(self.apply_button)

        self.cancel_button = QPushButton("Close")
        self.cancel_button.clicked.connect(self.close)
        self.layout.addWidget(self.cancel_button)

        self.update_image()

    def update_image(self):
        mode = self.mode_combo.currentText()

        if mode == "Center":
            self.edited_pixmap = QPixmap(self.target_size)
            self.edited_pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(self.edited_pixmap)
            offset_x = (self.target_size.width() - self.original_pixmap.width()) // 2
            offset_y = (self.target_size.height() - self.original_pixmap.height()) // 2
            painter.drawPixmap(offset_x, offset_y, self.original_pixmap)
            painter.end()
        elif mode == "Stretch":
            self.edited_pixmap = self.original_pixmap.scaled(
                self.target_size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
        elif mode == "Fit":
            self.edited_pixmap = self.original_pixmap.scaled(
                self.target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            # Ensure the pixmap matches target size with padding
            temp_pixmap = QPixmap(self.target_size)
            temp_pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(temp_pixmap)
            offset_x = (self.target_size.width() - self.edited_pixmap.width()) // 2
            offset_y = (self.target_size.height() - self.edited_pixmap.height()) // 2
            painter.drawPixmap(offset_x, offset_y, self.edited_pixmap)
            painter.end()
            self.edited_pixmap = temp_pixmap

        self.preview.setPixmap(
            self.edited_pixmap.scaled(
                self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
        )

    def accept(self):
        self.parent().set_uploaded_image(self.edited_pixmap)


class CameraPage(QWidget):
    request_file_dialog = Signal()

    def __init__(self, new_frame_callback: Callable[[np.ndarray], None] = lambda _: None):
        super().__init__()
        self.new_frame = new_frame_callback
        self.open_camera: cv2.VideoCapture | None = None
        self.open_camera_index: int | None = None
        self.resolution_size = QSize(640, 480)
        self.fps_value = 30.0
        self.uploaded_image: QPixmap | None = None
        self.editor_widget: ImageEditor | None = None

        self.root_layout = QVBoxLayout()
        self.setLayout(self.root_layout)

        self.form = QFormLayout()
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
        self.source.currentIndexChanged.connect(self.on_source_changed)
        self.source_layout.addWidget(self.source)

        self.source_refresh = QPushButton()
        self.source_refresh.setIconSize(QSize(18, 18))
        self.source_refresh.setIcon(icon(MDI7.refresh))
        self.source_refresh.setFixedSize(QSize(32, 32))
        self.source_refresh.clicked.connect(self.refresh_video_sources)
        self.source_layout.addWidget(self.source_refresh)

        self.upload_button = QPushButton("Upload Image")
        self.upload_button.setIcon(icon(MDI7.upload))
        self.upload_button.clicked.connect(self.trigger_file_dialog)
        self.upload_button.setEnabled(True)
        self.form.addRow("Image Upload", self.upload_button)

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

        self.request_file_dialog.connect(self.upload_image)

        self.refresh_video_sources()

    def trigger_file_dialog(self):
        if current_process().name != "MainProcess":
            self.request_file_dialog.emit()
        else:
            self.upload_image()

    @Slot()
    def upload_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if file_name:
            pixmap = QPixmap(file_name)
            if not pixmap.isNull():
                self.editor_widget = ImageEditor(pixmap, self.resolution_size, self)
                self.editor_widget.show()
            else:
                QMessageBox.warning(self, "Error", "Failed to load image")

    def set_uploaded_image(self, pixmap: QPixmap):
        self.uploaded_image = pixmap
        self.set_resolution(pixmap.width(), pixmap.height())
        self.editor_widget = None

    def on_source_changed(self, index):
        self.upload_button.setEnabled(index == 0)

    def set_resolution(self, width: int, height: int):
        self.resolution.setText(f"Resolution: {width}x{height}")
        self.resolution_size = QSize(width, height)
        self.frame = self.frame.scaled(
            QSize(width, height), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        if self.open_camera:
            self.open_camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution_size.width())
            self.open_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution_size.height())

    def set_fps(self, fps: float):
        self.fps.setText(f"FPS: {fps:.2f}")
        self.frame_timer_thread.interval_ms = int(1000 / fps)
        self.fps_value = fps
        if self.open_camera:
            self.open_camera.set(cv2.CAP_PROP_FPS, int(self.fps_value))

    def refresh_video_sources(self):
        current = self.source.currentText()
        self.source.clear()
        self.source.addItem("Uploaded Image")

        if sys.platform == "darwin":
            Logger().warning("macOS support for video passthrough is EXPERIMENTAL. Expect bugs.")

        cameras = enumerate_cameras()
        cameras.sort(key=lambda x: x.index, reverse=True)
        for camera in reversed(cameras):
            if camera.name not in [self.source.itemText(i) for i in range(self.source.count())]:
                self.source.addItem(camera.name, camera.index)

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

    def resizeEvent(self, event: QResizeEvent):  # noqa: N802
        self.update_scaled_pixmap()
        super().resizeEvent(event)

    def update_frame(self):
        if self.source.currentIndex() == 0:
            if self.open_camera:
                self.open_camera.release()
                self.open_camera = None
                self.open_camera_index = None

            if self.uploaded_image:
                self.frame = self.uploaded_image
            else:
                self.frame.fill(Qt.GlobalColor.darkRed)
                painter = QPainter(self.frame)
                painter.setPen(QColor("white"))
                font = QFont()
                font.setPointSize(60)
                font.setBold(True)
                painter.setFont(font)
                rect = self.frame.rect()
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No Image")
                painter.end()
        else:
            if self.open_camera_index != self.source.currentData(Qt.ItemDataRole.UserRole):
                self.open_camera.release() if self.open_camera else None
                self.open_camera_index = self.source.currentData(Qt.ItemDataRole.UserRole)
                self.open_camera = cv2.VideoCapture(self.open_camera_index)
                self.open_camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution_size.width())
                self.open_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution_size.height())
                self.open_camera.set(cv2.CAP_PROP_FPS, int(self.fps_value))
            if self.open_camera:
                ret, frame = self.open_camera.read()
                if ret:
                    height, width, channels = frame.shape
                    bytes_per_line = channels * width
                    cv_image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    self.frame = QPixmap.fromImage(
                        QImage(
                            cv_image_rgb.data,
                            width,
                            height,
                            bytes_per_line,
                            QImage.Format.Format_RGB888,
                        )
                    )
                else:
                    self.frame.fill(Qt.GlobalColor.darkRed)
                    painter = QPainter(self.frame)
                    painter.setPen(QColor("white"))
                    font = QFont()
                    font.setPointSize(60)
                    font.setBold(True)
                    painter.setFont(font)
                    rect = self.frame.rect()
                    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Camera Error")
        self.update_scaled_pixmap()

        qimage = self.frame.toImage().convertToFormat(QImage.Format.Format_RGB888)
        width = qimage.width()
        height = qimage.height()
        ptr = qimage.bits()
        arr = np.array(ptr, dtype=np.uint8).reshape((height, width, 3))
        mat = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        self.new_frame(mat)


ZMQ_SEND_BUFFER_SIZE = 1024 * 1024


@register_window_view("kevinbotlib.vision.cameras")
class CamerasWindowView(WindowView):
    new_tab = Signal(str)
    set_port = Signal(int)

    def __init__(self):
        super().__init__()
        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("CompactTabs")
        self.layout.addWidget(self.tabs)

        self.pages: dict[str, CameraPage] = {}
        self.camera_zmq_tcp_port: int | None = None
        self.camera_zmq_context: zmq.Context | None = None
        self.camera_zmq_socket: zmq.Socket | None = None
        self.new_tab.connect(self.create_tab)
        self.set_port.connect(self.set_zmq_port)

    @property
    def title(self) -> str:
        return "Cameras"

    def icon(self, dark_mode: bool) -> QIcon:
        super().icon(dark_mode)
        return icon(_MDI7.camera)

    def generate(self) -> QWidget:
        return self.widget

    def set_zmq_port(self, port: int):
        if not self.camera_zmq_tcp_port:
            self.camera_zmq_tcp_port = port
            self.camera_zmq_context = zmq.Context()
            self.camera_zmq_socket = self.camera_zmq_context.socket(zmq.PUB)
            self.camera_zmq_socket.setsockopt(zmq.SNDBUF, ZMQ_SEND_BUFFER_SIZE)
            self.camera_zmq_socket.bind(f"tcp://*:{self.camera_zmq_tcp_port}")

    def create_tab(self, camera_name: str):
        if camera_name not in self.pages:

            def send_frame(frame: np.ndarray) -> None:
                if not self.camera_zmq_context or not self.camera_zmq_socket:
                    Logger().warning("CameraZMQContext is not initialized.")
                    return

                sanitized_name = re.sub(r"[^A-Za-z0-9-_]", "_", camera_name)
                success, encoded_image = cv2.imencode(".jpg", frame)
                self.camera_zmq_socket.send_multipart([sanitized_name.encode("utf-8"), encoded_image.tobytes()])

            page = CameraPage(send_frame)
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
                case "port":
                    self.set_port.emit(payload["port"])
