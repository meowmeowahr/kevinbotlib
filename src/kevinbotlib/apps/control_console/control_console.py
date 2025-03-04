import sys

from PySide6.QtCore import Qt, QSettings, QCoreApplication, QCommandLineParser, QCommandLineOption
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
from kevinbotlib.comm import KevinbotCommClient
from kevinbotlib.logger import Level, Logger, LoggerConfiguration
from kevinbotlib.ui.theme import Theme, ThemeStyle
import kevinbotlib.apps.control_console.resources_rc


class ControlConsoleApplicationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"KevinbotLib Control Console {__version__}")
        self.setContentsMargins(4, 4, 4, 0)

        self.client = KevinbotCommClient()

        self.settings = QSettings("meowmeowahr", "kevinbotlib.console", self)

        # create settings keys if missing
        if "network.ip" not in self.settings.allKeys():
            self.settings.setValue("network.ip", "10.0.0.2")
        if "network.port" not in self.settings.allKeys():
            self.settings.setValue("network.port", 8765)
        if "application.theme" not in self.settings.allKeys():
            self.settings.setValue("application.theme", "System")

        self.theme = Theme(ThemeStyle.Dark)
        self.apply_theme()

        self.status = self.statusBar()
        self.status.setSizeGripEnabled(False)

        self.connection_status = QLabel("Robot Disconnected")
        self.status.addWidget(self.connection_status)

        self.ip_status = QLabel(str(self.settings.value("network.ip", "10.0.0.2", str)), alignment=Qt.AlignmentFlag.AlignCenter)
        self.status.addWidget(self.ip_status, 1)

        self.latency_status = QLabel("Latency: 0.00ms")
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
    logger = Logger()

    app = QApplication(sys.argv)
    app.setApplicationName("KevinbotLib Dashboard")
    app.setApplicationVersion(__version__)

    parser = QCommandLineParser()
    parser.addHelpOption()
    parser.addVersionOption()
    parser.addOption(QCommandLineOption(["V", "verbose"], "Enable verbose (DEBUG) logging"))
    parser.addOption(
        QCommandLineOption(["T", "trace"], QCoreApplication.translate("main", "Enable tracing (TRACE logging)"))
    )
    parser.process(app)

    logger = Logger()
    log_level = Level.INFO
    if parser.isSet("verbose"):
        log_level = Level.DEBUG
    elif parser.isSet("trace"):
        log_level = Level.TRACE

    logger.configure(LoggerConfiguration(level=log_level))
    
    kevinbotlib.apps.control_console.resources_rc.qInitResources()
    QFontDatabase.addApplicationFont(":/fonts/NotoSans-Regular.ttf")
    app.setFont(QFont("Noto Sans", app.font().pointSize()))
    window = ControlConsoleApplicationWindow()
    window.show()
    sys.exit(app.exec())
