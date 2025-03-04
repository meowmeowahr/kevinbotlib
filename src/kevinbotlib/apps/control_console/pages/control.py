from PySide6.QtWidgets import QWidget, QHBoxLayout, QGridLayout, QListWidget, QPushButton


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
        self.enable_layout.addWidget(self.enable_button, 0, 0)

        self.disable_button = QPushButton("Disable")
        self.enable_layout.addWidget(self.disable_button, 0, 1)

        self.estop_button = QPushButton("EMERGENCY STOP")
        self.enable_layout.addWidget(self.estop_button, 1, 0, 1, 2)