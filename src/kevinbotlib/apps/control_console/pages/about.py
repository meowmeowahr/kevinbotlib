from PySide6.QtWidgets import QWidget, QLabel, QTextEdit, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap

class ControlConsoleAboutTab(QWidget):
    def __init__(self):
        super().__init__()

        root_layout = QHBoxLayout()
        self.setLayout(root_layout)

        left_layout = QVBoxLayout()
        root_layout.addLayout(left_layout)

        app_icon = QLabel()
        app_icon.setPixmap(QPixmap(":/app_icons/icon.svg"))
        app_icon.setFixedSize(QSize(128, 128))
        app_icon.setScaledContents(True)
        left_layout.addWidget(app_icon)
        
        right_layout = QVBoxLayout()
        root_layout.addLayout(right_layout)

        title = QLabel("KevinbotLib Control Console")
        title.setObjectName("AboutSectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(title)
    