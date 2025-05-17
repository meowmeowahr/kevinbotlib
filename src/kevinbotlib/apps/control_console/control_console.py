import datetime
import sys
import time
from dataclasses import dataclass
from functools import partial
from queue import Queue
from threading import Thread

import ansi2html
import qtawesome as qta
from PySide6.QtCore import (
    QCommandLineOption,
    QCommandLineParser,
    QCoreApplication,
    QObject,
    QSettings,
    QSize,
    Qt,
    QThread,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QTabWidget,
)

import kevinbotlib.apps.control_console.resources_rc
from kevinbotlib.__about__ import __version__
from kevinbotlib.apps.control_console.pages.about import ControlConsoleAboutTab
from kevinbotlib.apps.control_console.pages.control import (
    AppState,
    ControlConsoleControlTab,
)
from kevinbotlib.apps.control_console.pages.controllers import ControlConsoleControllersTab
from kevinbotlib.apps.control_console.pages.metrics import ControlConsoleMetricsTab
from kevinbotlib.apps.control_console.pages.settings import ControlConsoleSettingsTab
from kevinbotlib.comm import AnyListSendable, CommPath, RedisCommClient, StringSendable
from kevinbotlib.joystick import DynamicJoystickSender, NullJoystick
from kevinbotlib.logger import Level, Logger, LoggerConfiguration
from kevinbotlib.remotelog import ANSILogReceiver
from kevinbotlib.ui.theme import Theme, ThemeStyle


class HeartbeatWorker(QObject):
    send_heartbeat = Signal()

    def __init__(self, client: RedisCommClient, key: str):
        super().__init__()
        self.client = client
        self.key = key
        self.send_heartbeat.connect(self.heartbeat)

    @Slot()
    def heartbeat(self):
        if not self.client.is_connected():
            return
        self.client.set(
            CommPath(self.key) / "heartbeat",
            StringSendable(value=str(datetime.datetime.now(datetime.timezone.utc)), timeout=1.5),
        )

class LatencyWorker(QObject):
    get_latency = Signal()
    latency = Signal(float)

    def __init__(self, client: RedisCommClient):
        super().__init__()
        self.client = client
        self.get_latency.connect(self.get)

    @Slot()
    def get(self):
        latency = self.client.get_latency()
        self.latency.emit(latency)


class ControlConsoleApplicationWindow(QMainWindow):
    def __init__(self, logger: Logger):
        super().__init__()
        self.setWindowTitle(f"KevinbotLib Control Console {__version__}")
        self.setWindowIcon(QIcon(":/app_icons/icon.svg"))
        self.setContentsMargins(4, 4, 4, 0)

        self.logger = logger
        if self.logger:
            self.logger.add_hook_ansi(self.log_hook)

        self.console_log_queue: Queue[str] = Queue(1000)

        self.settings = QSettings("meowmeowahr", "kevinbotlib.console", self)

        # create settings keys if missing
        if "network.ip" not in self.settings.allKeys():
            self.settings.setValue("network.ip", "10.0.0.2")
        if "network.port" not in self.settings.allKeys():
            self.settings.setValue("network.port", 6379)
        if "application.theme" not in self.settings.allKeys():
            self.settings.setValue("application.theme", "System")

        self._ctrl_status_key = "%ControlConsole/status"
        self._ctrl_request_key = "%ControlConsole/request"
        self._ctrl_heartbeat_key = "%ControlConsole/heartbeat"
        self._ctrl_controller_key = "%ControlConsole/joystick/{0}"
        self._ctrl_metrics_key = "%ControlConsole/metrics"
        self._ctrl_logs_key = "%ControlConsole/logs"
        self._ctrl_batteries_key = "%ControlConsole/batteries"

        self.client = RedisCommClient(
            host=str(self.settings.value("network.ip", "10.0.0.2", str)),
            port=int(self.settings.value("network.port", 6379, int)),  # type: ignore
            on_connect=self.on_connect,
            on_disconnect=self.on_disconnect,
        )

        self.logrx = ANSILogReceiver(self.on_log, self.client, self._ctrl_logs_key)

        self.joystick_senders: list[DynamicJoystickSender] = []
        for i in range(8):
            sender = DynamicJoystickSender(
                self.client, partial(self.get_joystick, i), key=self._ctrl_controller_key.format(i)
            )
            sender.stop()
            self.joystick_senders.append(sender)

        self.heartbeat_thread = QThread(self)
        self.heartbeat_worker = HeartbeatWorker(self.client, self._ctrl_heartbeat_key)
        self.heartbeat_worker.moveToThread(self.heartbeat_thread)
        self.heartbeat_thread.start()

        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.setInterval(200)
        self.heartbeat_timer.timeout.connect(self.heartbeat_worker.send_heartbeat)
        self.heartbeat_timer.start()

        self.latency_thread = QThread(self)
        self.latency_worker = LatencyWorker(self.client)
        self.latency_worker.moveToThread(self.latency_thread)
        self.latency_thread.start()
        self.latency_worker.latency.connect(self.update_latency)

        self.latency_timer = QTimer()
        self.latency_timer.setInterval(1000)
        self.latency_timer.timeout.connect(self.latency_worker.get_latency.emit)
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
        self.tabs.setIconSize(QSize(20, 20))
        self.setCentralWidget(self.tabs)

        self.settings_tab = ControlConsoleSettingsTab(self.settings, self)
        self.settings_tab.settings_changed.connect(self.settings_changed)

        self.control = ControlConsoleControlTab(
            self.client, self._ctrl_status_key, self._ctrl_request_key, self._ctrl_batteries_key
        )
        self.controllers_tab = ControlConsoleControllersTab()
        self.metrics_tab = ControlConsoleMetricsTab(self.client, self._ctrl_metrics_key)

        self.tabs.addTab(self.control, qta.icon("mdi6.robot"), "Run")
        self.tabs.addTab(self.controllers_tab, qta.icon("mdi6.gamepad-variant"), "Controllers")
        self.tabs.addTab(self.metrics_tab, qta.icon("mdi6.speedometer"), "Metrics")
        self.tabs.addTab(self.settings_tab, qta.icon("mdi6.cog"), "Settings")
        self.tabs.addTab(ControlConsoleAboutTab(self.theme), qta.icon("mdi6.information"), "About")

        self.connection_governor_thread = Thread(target=self.connection_governor, daemon=True, name="KevinbotLib.Console.Connection.Governor")
        self.connection_governor_thread.start()

        self.log_timer = QTimer()
        self.log_timer.setInterval(250)
        self.log_timer.timeout.connect(self.update_logs)
        self.log_timer.start()

    def connection_governor(self):
        while True:
            if not self.client.is_connected():
                for sender in self.joystick_senders:
                    sender.stop()
                self.client.connect()
            time.sleep(2)

    def get_joystick(self, index: int):
        controllers = list(self.controllers_tab.ordered_controllers.values())
        return controllers[index] if index < len(controllers) else NullJoystick()

    def log_hook(self, data: str):
        self.console_log_queue.put(ansi2html.Ansi2HTMLConverter(scheme="osx").convert(data.strip()))

    def on_log(self, ansi: str):
        self.console_log_queue.put(ansi2html.Ansi2HTMLConverter(scheme="osx").convert(ansi.strip()))

    def update_logs(self):
        if not self.control:
            return

        while not self.console_log_queue.empty():
            self.control.logs.append(self.console_log_queue.get())
            if self.control.autoscroll_checkbox.isChecked():
                self.control.logs.verticalScrollBar().setValue(self.control.logs.verticalScrollBar().maximum())

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
            qta.dark(QApplication.instance())
        else:
            qta.light(QApplication.instance())

    def settings_changed(self):
        self.ip_status.setText(str(self.settings.value("network.ip", "10.0.0.2", str)))

        if self.client.host != str(self.settings.value("network.ip", "10.0.0.2", str)):
            self.client.host = str(self.settings.value("network.ip", "10.0.0.2", str))
        if self.client.port != int(self.settings.value("network.port", 6379, int)):
            self.client.port = int(self.settings.value("network.port", 6379, int))  # type: ignore

    def on_connect(self):
        self.logger.info("Comms are up!")
        self.control.state.set(AppState.WAITING)
        for sender in self.joystick_senders:
            sender.start()
        self.logger.info("Started robot log session")
        self.logrx.start()
        self.client.subscribe(
            CommPath(self._ctrl_batteries_key),
            AnyListSendable,
            self.control.on_battery_update,
        )

    def on_disconnect(self):
        self.control.clear_opmodes()
        for sender in self.joystick_senders:
            sender.stop()
        self.control.state.set(AppState.NO_COMMS)
        self.metrics_tab.text.clear()

    def update_latency(self, latency: float | None):
        if latency:
            self.latency_status.setText(f"Latency: {latency:.2f}ms")
        else:
            self.latency_status.setText("Latency: --.--ms")

    def closeEvent(self, event: QCloseEvent):  # noqa: N802
        self.heartbeat_timer.stop()
        self.heartbeat_thread.quit()
        self.heartbeat_thread.moveToThread(self.thread())
        self.latency_timer.stop()
        self.latency_thread.quit()
        self.latency_thread.moveToThread(self.thread())
        event.accept()


@dataclass
class ControlConsoleApplicationStartupArguments:
    verbose: bool = False
    trace: bool = True


class ControlConsoleApplicationRunner:
    def __init__(self, args: ControlConsoleApplicationStartupArguments | None = None):
        self.logger = Logger()
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("KevinbotLib Dashboard")
        self.app.setApplicationVersion(__version__)
        self.app.setStyle("Fusion")  # can solve some platform-specific issues

        self.configure_logger(args)
        self.window = None

    def configure_logger(self, args: ControlConsoleApplicationStartupArguments | None):
        if args is None:
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
            parser.process(self.app)

            log_level = Level.INFO
            if parser.isSet("verbose"):
                log_level = Level.DEBUG
            elif parser.isSet("trace"):
                log_level = Level.TRACE
        else:
            log_level = Level.INFO
            if args.verbose:
                log_level = Level.DEBUG
            elif args.trace:
                log_level = Level.TRACE

        self.logger.configure(LoggerConfiguration(level=log_level))

    def run(self):
        kevinbotlib.apps.control_console.resources_rc.qInitResources()
        self.window = ControlConsoleApplicationWindow(self.logger)
        self.window.show()
        sys.exit(self.app.exec())


def execute(args: ControlConsoleApplicationStartupArguments | None):
    runner = ControlConsoleApplicationRunner(args)
    runner.run()


if __name__ == "__main__":
    execute(None)
