import os

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPalette
from PySide6.QtWidgets import QLabel, QWidget


class DragDropLabel(QLabel):
    path_changed = Signal(str)

    def __init__(self, text: str = "", parent: QWidget = None, exts: tuple[str] = (".pem", ".key", ".ppk", ".rsa")):
        super().__init__(parent)
        self.extensions = exts
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.idle_color = "#1F1F22" if not parent else parent.palette().color(QPalette.ColorRole.Base).name()
        self.setStyleSheet(f"border: 2px dashed {self.idle_color}; min-height: 50px; border-radius: 4px;")
        self.setAcceptDrops(True)
        self.setText(text)

    def dragEnterEvent(self, event: QDragEnterEvent):  # noqa: N802
        mime_data: QMimeData = event.mimeData()

        # Check if the drag contains URLs (files)
        if mime_data.hasUrls():
            # Check if all URLs are valid image files
            valid_extensions = self.extensions
            if all(url.toLocalFile().lower().endswith(valid_extensions) for url in mime_data.urls()):
                event.acceptProposedAction()
                self.setStyleSheet("border: 2px dashed green; min-height: 50px; border-radius: 4px;")
                return

        event.ignore()
        self.setStyleSheet("border: 2px dashed red; min-height: 50px; border-radius: 4px;")

    def dragLeaveEvent(self, _event):  # noqa: N802
        self.setStyleSheet(f"border: 2px dashed {self.idle_color}; min-height: 50px; border-radius: 4px;")

    def dropEvent(self, event: QDropEvent):  # noqa: N802
        mime_data: QMimeData = event.mimeData()

        if mime_data.hasUrls():
            event.acceptProposedAction()

            # Process each dropped file
            for url in mime_data.urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    self.path_changed.emit(file_path)

        self.setStyleSheet("border: 2px dashed #1F1F22; min-height: 50px; border-radius: 4px;")
