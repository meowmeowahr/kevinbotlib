import sys
from queue import Queue

import ansi2html
from PySide6.QtCore import (
    QCommandLineOption,
    QCommandLineParser,
    QCoreApplication,
    QSettings,
    Qt,
    QTimer,
)
from PySide6.QtGui import QIcon, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QTabWidget,
)
import qtawesome as qta

import kevinbotlib.apps.control_console.resources_rc
from kevinbotlib.__about__ import __version__
from kevinbotlib.apps.control_console.pages.about import ControlConsoleAboutTab
from kevinbotlib.apps.control_console.pages.control import (
    AppState,
    ControlConsoleControlTab,
)
from kevinbotlib.apps.control_console.pages.controllers import ControlConsoleControllersTab
from kevinbotlib.apps.control_console.pages.settings import ControlConsoleSettingsTab
from kevinbotlib.comm import CommPath, KevinbotCommClient, StringSendable
from kevinbotlib.logger import Level, Logger, LoggerConfiguration
from kevinbotlib.ui.theme import Theme, ThemeStyle


class ControlConsoleApplicationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"KevinbotLib Control Console {__version__}")
        self.setWindowIcon(QIcon(":/app_icons/icon.svg"))
        self.setContentsMargins(4, 4, 4, 0)

        logger.add_hook_ansi(self.log_hook)

        self.console_log_queue: Queue[str] = Queue(1000)

        self.settings = QSettings("meowmeowahr", "kevinbotlib.console", self)

        # create settings keys if missing
        if "network.ip" not in self.settings.allKeys():
            self.settings.setValue("network.ip", "10.0.0.2")
        if "network.port" not in self.settings.allKeys():
            self.settings.setValue("network.port", 8765)
        if "application.theme" not in self.settings.allKeys():
            self.settings.setValue("application.theme", "System")

        self._ctrl_status_key = "%ControlConsole/status"
        self._ctrl_request_key = "%ControlConsole/request"
        self._ctrl_heartbeat_key = "%ControlConsole/heartbeat"

        self.client = KevinbotCommClient(
            host=str(self.settings.value("network.ip", "10.0.0.2", str)),
            port=int(self.settings.value("network.port", 8765, int)),  # type: ignore
            on_connect=self.on_connect,
            on_disconnect=self.on_disconnect,
        )

        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.setInterval(100)
        self.heartbeat_timer.timeout.connect(self.heartbeat)
        self.heartbeat_timer.start()

        self.latency_timer = QTimer()
        self.latency_timer.setInterval(1000)
        self.latency_timer.timeout.connect(self.update_latency)
        self.latency_timer.start()

        self.theme = Theme(ThemeStyle.Dark)
        self.apply_theme()

        self.status = self.statusBar()
        self.status.setSizeGripEnabled(False)

        self.ip_status = QLabel(
            str(self.settings.value("network.ip", "10.0.0.2", str)),
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        self.status.addWidget(self.ip_status)

        self.latency_status = QLabel("Latency: -.--ms")
        self.status.addPermanentWidget(self.latency_status)

        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

        self.settings_tab = ControlConsoleSettingsTab(self.settings, self)
        self.settings_tab.settings_changed.connect(self.settings_changed)

        self.control = ControlConsoleControlTab(self.client, self._ctrl_status_key, self._ctrl_request_key)
        self.controllers_tab = ControlConsoleControllersTab()


        self.tabs.addTab(self.control, qta.icon("mdi6.robot"), "Run")
        self.tabs.addTab(self.controllers_tab, qta.icon("mdi6.gamepad-variant"), "Controllers")
        self.tabs.addTab(self.settings_tab, qta.icon("mdi6.cog"), "Settings")
        self.tabs.addTab(ControlConsoleAboutTab(), qta.icon("mdi6.information"), "About")

        self.client.connect()

        self.log_timer = QTimer()
        self.log_timer.setInterval(250)
        self.log_timer.timeout.connect(self.update_logs)
        self.log_timer.start()

    def log_hook(self, data: str):
        self.console_log_queue.put(ansi2html.Ansi2HTMLConverter(scheme="osx").convert(data.strip()))

    def update_logs(self):
        if not self.control:
            return

        while not self.console_log_queue.empty():
            self.control.logs.append(self.console_log_queue.get())
            if self.control.autoscroll_checkbox.isChecked():
                self.control.logs.moveCursor(QTextCursor.MoveOperation.End)

    def apply_theme(self):
        theme_name = self.settings.value("application.theme", "Dark")
        if theme_name == "Dark":
            self.theme.set_style(ThemeStyle.Dark)
        elif theme_name == "Light":
            self.theme.set_style(ThemeStyle.Light)
        else:
            self.theme.set_style(ThemeStyle.System)
        self.theme.apply(self)

        if self.theme.is_dark():
            qta.dark(app)
        else:
            qta.light(app)

    def settings_changed(self):
        self.ip_status.setText(str(self.settings.value("network.ip", "10.0.0.2", str)))

        self.client.host = str(self.settings.value("network.ip", "10.0.0.2", str))
        self.client.port = int(self.settings.value("network.port", 8765, int))  # type: ignore

    def on_connect(self):
        self.control.state.set(AppState.WAITING)

    def on_disconnect(self):
        self.control.clear_opmodes()
        self.control.state.set(AppState.NO_COMMS)

    def heartbeat(self):
        if not self.client.is_connected():
            return

        ws = self.client.websocket
        if ws:
            self.client.send(
                CommPath(self._ctrl_heartbeat_key) / "heartbeat",
                StringSendable(value=str(ws.id), timeout=0.25),
            )
        else:
            self.client.delete(CommPath(self._ctrl_heartbeat_key) / "heartbeat")

    def update_latency(self):
        if self.client.websocket:
            self.latency_status.setText(f"Latency: {self.client.websocket.latency:.2f}ms")


if __name__ == "__main__":
    logger = Logger()

    app = QApplication(sys.argv)
    app.setApplicationName("KevinbotLib Dashboard")
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion") # can solve some platform-specific issues

    parser = QCommandLineParser()
    parser.addHelpOption()
    parser.addVersionOption()
    parser.addOption(QCommandLineOption(["V", "verbose"], "Enable verbose (DEBUG) logging"))
    parser.addOption(
        QCommandLineOption(
            ["T", "trace"],
            QCoreApplication.translate("main", "Enable tracing (TRACE logging)"),
        )
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
    window = ControlConsoleApplicationWindow()
    window.show()
    sys.exit(app.exec())
