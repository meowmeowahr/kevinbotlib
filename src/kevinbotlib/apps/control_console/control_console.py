import sys

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QLabel,
)
from PySide6.QtGui import QFontDatabase, QFont

from kevinbotlib.__about__ import __version__
from kevinbotlib.apps.control_console.pages.about import ControlConsoleAboutTab
from kevinbotlib.apps.control_console.pages.control import ControlConsoleControlTab
from kevinbotlib.apps.control_console.pages.settings import ControlConsoleSettingsTab
from kevinbotlib.ui.theme import Theme, ThemeStyle
import kevinbotlib.apps.control_console.resources_rc


class ControlConsoleApplicationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"KevinbotLib Control Console {__version__}")
        self.setContentsMargins(4, 4, 4, 0)

        self.settings = QSettings("meowmeowahr", "kevinbotlib.console", self)
        self.theme = Theme(ThemeStyle.Dark)
        self.apply_theme()

        self.status = self.statusBar()
        self.status.setSizeGripEnabled(False)

        self.connection_status = QLabel("Robot Disconnected")
        self.status.addWidget(self.connection_status)

        self.ip_status = QLabel(str(self.settings.value("network.ip", "10.0.0.2", str)), alignment=Qt.AlignmentFlag.AlignCenter)
        self.status.addWidget(self.ip_status, 1)

        self.latency_status = QLabel("Latency: 0.00")
        self.status.addPermanentWidget(self.latency_status)

        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

        self.settings_tab = ControlConsoleSettingsTab(self.settings, self)
        self.settings_tab.settings_changed.connect(self.settings_changed)

        self.tabs.addTab(ControlConsoleControlTab(), "Control")
        self.tabs.addTab(self.settings_tab, "Settings")
        self.tabs.addTab(ControlConsoleAboutTab(), "About")

    def apply_theme(self):
        theme_name = self.settings.value("application.theme", "Dark")
        if theme_name == "Dark":
            self.theme.set_style(ThemeStyle.Dark)
        elif theme_name == "Light":
            self.theme.set_style(ThemeStyle.Light)
        else:
            self.theme.set_style(ThemeStyle.System)
        self.theme.apply(self)

    def settings_changed(self):
        self.ip_status.setText(str(self.settings.value("network.ip", "10.0.0.2", str)))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    kevinbotlib.apps.control_console.resources_rc.qInitResources()
    QFontDatabase.addApplicationFont(":/fonts/NotoSans-Regular.ttf")
    app.setFont(QFont("Noto Sans", app.font().pointSize()))
    window = ControlConsoleApplicationWindow()
    window.show()
    sys.exit(app.exec())
