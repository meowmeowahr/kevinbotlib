from PySide6.QtCore import Signal
from PySide6.QtGui import QFont, QPixmap, Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from kevinbotlib.apps.common.dnd import DragDropLabel


class UploadForm(QWidget):
    load_file_path = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.file_path = ""

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.root_layout.addStretch()

        self.icon = QLabel()
        self.icon.setPixmap(QPixmap(":/app_icons/log-viewer-128.svg"))
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.root_layout.addWidget(self.icon)

        self.title = QLabel("Select Log File")
        self.title.setFont(QFont(self.font().family(), 20, QFont.Weight.Light))
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.root_layout.addWidget(self.title)

        self.root_layout.addSpacing(16)

        self.file_dnd = DragDropLabel("Drop Log File\n(or click to pick)", self, (".log",))
        self.file_dnd.mouseReleaseEvent = self.load_file
        self.file_dnd.path_changed.connect(self.set_key_path)
        self.root_layout.addWidget(self.file_dnd)

        self.connect_button = QPushButton("Load")
        self.connect_button.clicked.connect(self.attempt_load)
        self.connect_button.setDisabled(True)
        self.root_layout.addWidget(self.connect_button)

        self.root_layout.addStretch()

    def load_file(self, _event):
        path, _ = QFileDialog.getOpenFileName(self, "Open KevinbotLib Log File", "", "Log Files (*.log)")
        if path:
            self.set_key_path(path)

    def set_key_path(self, path):
        self.file_path = path
        self.file_dnd.setText(path)
        self.check_button_enabled()

    def attempt_load(self):
        self.load_file_path.emit(self.file_path)

    def check_button_enabled(self):
        self.connect_button.setDisabled(not self.file_path)
