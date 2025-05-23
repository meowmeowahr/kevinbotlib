from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QPushButton, QTabWidget, QTextEdit, QVBoxLayout

from kevinbotlib.licenses import get_licenses
from kevinbotlib.ui.widgets.battery import Battery, BatteryGrapher, BatteryManager


class LicenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Licenses")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # License tabs
        license_tabs = QTabWidget()
        license_tabs.setObjectName("CompactTabs")
        layout.addWidget(license_tabs)

        # Add license content
        for dependency, lic in get_licenses().items():
            license_tabs.addTab(QTextEdit(plainText=lic, readOnly=True), dependency)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)


__all__ = ["Battery", "BatteryGrapher", "BatteryManager", "LicenseDialog"]
