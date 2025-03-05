from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QTabWidget, QTextEdit, QVBoxLayout, QWidget

from kevinbotlib import __about__
from kevinbotlib.licenses import get_licenses


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

        version = QLabel(__about__.__version__)
        version.setObjectName("AboutSectionVersion")
        right_layout.addWidget(version)

        license_tabs = QTabWidget()
        license_tabs.setObjectName("CompactTabs")
        right_layout.addWidget(license_tabs)

        license_tabs.addTab(QTextEdit(plainText=get_licenses()["kevinbotlib"], readOnly=True), "KevinbotLib Control Console")
        for dependency, license in get_licenses().items():
            license_tabs.addTab(QTextEdit(plainText=license, readOnly=True), dependency)
