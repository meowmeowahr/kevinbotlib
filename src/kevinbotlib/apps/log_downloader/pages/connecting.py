import qtawesome as qta
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ConnectingPage(QWidget):
    def __init__(self):
        super().__init__()

        self.root_layout = QVBoxLayout()
        self.setLayout(self.root_layout)

        self.spinner = qta.IconWidget()
        self.spinner.setIconSize(QSize(128, 125))
        self.spinner.setIcon(qta.icon("mdi6.timer-sand"))
        self.spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.root_layout.addWidget(self.spinner)

        self.text = QLabel("Connecting...")
        self.text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text.setFont(QFont(self.font().family(), 16))
        self.root_layout.addWidget(self.text)
