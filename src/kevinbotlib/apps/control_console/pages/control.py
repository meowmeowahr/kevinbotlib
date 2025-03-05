from PySide6.QtCore import QSize
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QListWidget, QPushButton, QWidget


class ControlConsoleControlTab(QWidget):
    def __init__(self):
        super().__init__()

        root_layout = QHBoxLayout()
        self.setLayout(root_layout)

        self.opmode_selector = QListWidget()
        root_layout.addWidget(self.opmode_selector)

        self.enable_layout = QGridLayout()
        root_layout.addLayout(self.enable_layout)

        self.enable_button = QPushButton("Enable")
        self.enable_button.setObjectName("EnableButton")
        self.enable_button.setFixedSize(QSize(128, 84))
        self.enable_layout.addWidget(self.enable_button, 0, 0)

        self.disable_button = QPushButton("Disable")
        self.disable_button.setObjectName("DisableButton")
        self.disable_button.setFixedSize(QSize(128, 84))
        self.enable_layout.addWidget(self.disable_button, 0, 1)

        self.estop_button = QPushButton("EMERGENCY STOP")
        self.estop_button.setObjectName("EstopButton")
        self.estop_button.setFixedHeight(96)
        self.enable_layout.addWidget(self.estop_button, 1, 0, 1, 2)
