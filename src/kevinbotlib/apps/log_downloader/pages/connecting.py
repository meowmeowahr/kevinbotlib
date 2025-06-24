from fonticon_mdi7 import MDI7
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from kevinbotlib.apps import get_icon as icon


class ConnectingPage(QWidget):
    def __init__(self):
        super().__init__()

        self.root_layout = QVBoxLayout()
        self.setLayout(self.root_layout)

        self.spinner = QLabel()
        self.spinner.setPixmap(icon(MDI7.timer_sand).pixmap(128, 125))
        self.spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.root_layout.addWidget(self.spinner)

        self.text = QLabel("Connecting...")
        self.text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text.setFont(QFont(self.font().family(), 16))
        self.root_layout.addWidget(self.text)
