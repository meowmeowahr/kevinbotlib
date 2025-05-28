import qtawesome as qta
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from kevinbotlib import __about__
from kevinbotlib.ui.theme import Theme
from kevinbotlib.ui.widgets import LicenseDialog


class ControlConsoleAboutTab(QWidget):
    def __init__(self, _theme: Theme):
        super().__init__()

        # Main layout
        root_layout = QHBoxLayout()
        root_layout.setSpacing(20)  # Add some spacing between elements
        self.setLayout(root_layout)

        # Left side (icon)
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        root_layout.addLayout(left_layout)

        left_layout.addStretch()

        app_icon = QLabel()
        app_icon.setPixmap(QPixmap(":/app_icons/console.svg"))
        app_icon.setFixedSize(QSize(128, 128))
        app_icon.setScaledContents(True)
        left_layout.addWidget(app_icon)

        left_layout.addStretch()

        # Right side (content)
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)  # Consistent spacing
        root_layout.addLayout(right_layout, stretch=1)  # Allow stretching

        right_layout.addStretch()

        # Title
        title = QLabel("KevinbotLib Control Console")
        title.setObjectName("AboutSectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        right_layout.addWidget(title)

        # Version
        version = QLabel(f"Version {__about__.__version__}")
        version.setObjectName("AboutSectionVersion")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet("font-size: 16px; color: gray;")
        right_layout.addWidget(version)

        # Button layout for About Qt and Licenses
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        right_layout.addLayout(button_layout)

        # About Qt button
        about_qt_btn = QPushButton("About Qt")
        about_qt_btn.setMaximumWidth(200)
        about_qt_btn.clicked.connect(QApplication.aboutQt)
        about_qt_btn.setIcon(qta.icon("mdi6.information-box"))
        button_layout.addWidget(about_qt_btn)

        # License button
        license_btn = QPushButton("View Licenses")
        license_btn.setMaximumWidth(200)
        license_btn.clicked.connect(self.show_licenses)
        license_btn.setIcon(qta.icon("mdi6.gavel"))
        button_layout.addWidget(license_btn)

        right_layout.addStretch()

    def show_licenses(self):
        """Show the license dialog."""
        dialog = LicenseDialog(self)
        dialog.exec()
