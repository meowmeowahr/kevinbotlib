from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from kevinbotlib.ui.widgets import LicenseDialog


class AboutDialog(QDialog):
    def __init__(
        self,
        app_name: str,
        app_description: str,
        app_version: str,
        app_license: str,
        app_icon: QIcon | None = None,
        cright: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"About {app_name}")
        self.setModal(True)

        licenses_dialog = LicenseDialog(self)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.top_layout = QHBoxLayout()
        layout.addLayout(self.top_layout)

        if app_icon:
            icon_label = QLabel()
            icon_label.setPixmap(app_icon.pixmap(128, 128))
            self.top_layout.addWidget(icon_label)

        self.top_layout.addSpacing(32)

        top_titles_layout = QVBoxLayout()
        self.top_layout.addLayout(top_titles_layout)
        self.top_layout.addStretch()

        top_titles_layout.addStretch()

        title_label = QLabel(app_name)
        title_label.setFont(QFont(self.font().family(), 16, QFont.Weight.DemiBold))
        top_titles_layout.addWidget(title_label)

        description_label = QLabel(app_description)
        top_titles_layout.addWidget(description_label)

        top_titles_layout.addStretch()

        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addStretch()

        version_label = QLabel(f"Version: {app_version}")
        layout.addWidget(version_label)

        license_label = QLabel(f"License: {app_license}")
        layout.addWidget(license_label)

        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        layout.addStretch()

        licenses_layout = QHBoxLayout()
        layout.addLayout(licenses_layout)

        licenses_button = QPushButton("Open Source Licenses")
        licenses_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        licenses_button.clicked.connect(licenses_dialog.exec)
        licenses_layout.addWidget(licenses_button)

        about_qt = QPushButton("About Qt")
        about_qt.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        about_qt.clicked.connect(QApplication.aboutQt)
        licenses_layout.addWidget(about_qt)

        layout.addStretch()
        bottom_layout = QHBoxLayout()
        layout.addLayout(bottom_layout)

        if cright:
            copyright_text = QLabel(cright)
            bottom_layout.addWidget(copyright_text)

        bottom_layout.addStretch()

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.close)
        bottom_layout.addWidget(ok_button)
