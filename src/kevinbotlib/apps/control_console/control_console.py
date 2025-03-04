import sys

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
)

from kevinbotlib.__about__ import __version__
from kevinbotlib.apps.control_console.pages.control import ControlConsoleControlTab
from kevinbotlib.apps.control_console.pages.settings import ControlConsoleSettingsTab
from kevinbotlib.ui.theme import Theme, ThemeStyle


class ControlConsoleApplicationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"KevinbotLib Control Console {__version__}")
        self.setContentsMargins(4, 4, 4, 4)

        self.settings = QSettings("meowmeowahr", "kevinbotlib.console", self)
        self.theme = Theme(ThemeStyle.Dark)
        self.apply_theme()

        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

        self.tabs.addTab(ControlConsoleControlTab(), "Control")
        self.tabs.addTab(ControlConsoleSettingsTab(self.settings, self), "Settings")

    def apply_theme(self):
        theme_name = self.settings.value("application.theme", "Dark")
        if theme_name == "Dark":
            self.theme.set_style(ThemeStyle.Dark)
        elif theme_name == "Light":
            self.theme.set_style(ThemeStyle.Light)
        else:
            self.theme.set_style(ThemeStyle.System)
        self.theme.apply(self)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ControlConsoleApplicationWindow()
    window.show()
    sys.exit(app.exec())
