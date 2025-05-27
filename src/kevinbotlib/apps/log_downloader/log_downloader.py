import os
import socket
import sys
import time
from binascii import hexlify
from dataclasses import dataclass
from enum import IntEnum

import paramiko
import qtawesome as qta
from PySide6.QtCore import (
    QCommandLineOption,
    QCommandLineParser,
    QCoreApplication,
    QObject,
    QSettings,
    QThread,
    Signal,
    Slot,
)
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
)

import kevinbotlib.apps.log_downloader.resources_rc
from kevinbotlib.__about__ import __version__
from kevinbotlib.apps.common.abc import ThemableWindow
from kevinbotlib.apps.common.about import AboutDialog
from kevinbotlib.apps.common.settings_rows import Divider, UiColorSettingsSwitcher
from kevinbotlib.apps.common.toast import NotificationWidget, Severity
from kevinbotlib.apps.common.url_scheme import setup_url_scheme
from kevinbotlib.apps.log_downloader.pages.connecting import ConnectingPage
from kevinbotlib.apps.log_downloader.pages.connection import ConnectionForm
from kevinbotlib.apps.log_downloader.pages.viewer import LogViewer
from kevinbotlib.logger import Level, Logger, LoggerConfiguration
from kevinbotlib.logger.downloader import RemoteLogDownloader
from kevinbotlib.ui.theme import Theme, ThemeStyle


class SettingsWindow(QDialog):
    on_applied = Signal()

    def __init__(self, parent: "Application", settings: QSettings):
        super().__init__(parent=parent)
        self.setModal(True)

        self.settings = settings

        self.root_layout = QVBoxLayout()
        self.setLayout(self.root_layout)

        self.form = QFormLayout()
        self.root_layout.addLayout(self.form)

        self.form.addRow(Divider("Theme"))

        self.form.addRow(
            NotificationWidget(
                "Warning", "A restart is required to fully apply the theme", Severity.Warning.value, 0, bg=False
            )
        )

        self.theme = UiColorSettingsSwitcher(settings, "theme", parent)
        self.form.addRow("Theme", self.theme)

        self.button_layout = QHBoxLayout()
        self.button_layout.addStretch()
        self.root_layout.addLayout(self.button_layout)

        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply)
        self.button_layout.addWidget(self.apply_button)

        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.close)
        self.button_layout.addWidget(self.exit_button)

    def apply(self):
        self.on_applied.emit()


class HostKeyOptionReturn(IntEnum):
    Unknown = 0
    Accept = 1
    Abort = 2


class ConnectionWorker(QObject):
    connected = Signal()
    error = Signal(str)
    start_password = Signal(str, int, str, str)
    start_key = Signal(str, int, str, paramiko.RSAKey)
    ask_host_key = Signal(object, str, str, str)
    return_host_key = Signal(HostKeyOptionReturn)

    class HostKeyPolicy(paramiko.MissingHostKeyPolicy):
        def __init__(self, parent: "ConnectionWorker"):
            super().__init__()
            self.parent = parent
            self.key_return = HostKeyOptionReturn.Unknown

        def missing_host_key(self, _client, hostname, key):
            hostname_str = str(hostname)
            key_name = key.get_name()
            key_fingerprint = hexlify(key.get_fingerprint()).decode()

            Logger().warning(f"Unknown {key_name} host key for {hostname_str}: {key_fingerprint}")

            self.parent.ask_host_key.emit(self, hostname_str, key_name, key_fingerprint)
            while self.key_return == HostKeyOptionReturn.Unknown:
                time.sleep(0.1)
            match self.key_return:
                case HostKeyOptionReturn.Abort:
                    msg = f"Server {hostname!r} not found in known_hosts"
                    raise paramiko.SSHException(msg)
                case HostKeyOptionReturn.Accept:
                    return
            return

    def __init__(self, client: RemoteLogDownloader, parent):
        super().__init__()
        self.client = client
        self.window = parent
        self.start_password.connect(self.run_password)
        self.start_key.connect(self.run_key)
        self.policy = ConnectionWorker.HostKeyPolicy(self)

    @Slot(str, int, str, paramiko.RSAKey)
    def run_key(self, host: str, port: int, user: str, key: paramiko.RSAKey):
        try:
            self.client.connect_with_key(
                host,
                user,
                key,
                port,
                missing_host_key_policy=self.policy,
            )
        except paramiko.AuthenticationException:
            self.error.emit("Authentication failed")
            return
        except TimeoutError:
            self.error.emit("Connection timed out")
            return
        except socket.gaierror as e:
            self.error.emit(f"Could not resolve hostname: {e!r}")
            return
        except paramiko.SSHException as e:
            self.error.emit(f"Connection failed: {e!r}")
            return
        self.connected.emit()

    @Slot(str, int, str, str)
    def run_password(self, host: str, port: int, user: str, password: str):
        try:
            self.client.connect_with_password(
                host,
                user,
                password,
                port,
                missing_host_key_policy=self.policy,
            )
        except paramiko.AuthenticationException:
            self.error.emit("Authentication failed")
            return
        except TimeoutError:
            self.error.emit("Connection timed out")
            return
        except socket.gaierror as e:
            self.error.emit(f"Could not resolve hostname: {e!r}")
            return
        except paramiko.SSHException as e:
            self.error.emit(f"Connection failed: {e!r}")
            return
        self.connected.emit()


class Application(ThemableWindow):
    def __init__(self, app: QApplication, logger: Logger):
        super().__init__()
        self.app = app
        self.logger = logger

        self.connect_worker = None
        self.connect_thread = None

        self.downloader = RemoteLogDownloader()

        self.setWindowIcon(QIcon(":/app_icons/log-downloader-small.svg"))
        self.setWindowIcon(QIcon(":/app_icons/log-downloader-small.svg"))

        self.settings = QSettings("kevinbotlib", "logdownloader")
        self.theme = Theme(ThemeStyle.System)
        self.apply_theme()

        self.settings_window = SettingsWindow(self, self.settings)

        self.about_window = AboutDialog(
            "KevinbotLib Log Downloader",
            "Download and View Logs from a KevinbotLib Robot",
            __version__,
            "\nSource code is licensed under the GNU LGPLv3\nBinaries are licensed under the GNU GPLv3 due to some GPL components\nSee 'Open Source Licenses' for more details...",
            QIcon(":/app_icons/log-downloader.svg"),
            "Copyright © 2025 Kevin Ahr and contributors",
            self,
        )

        self.menu = self.menuBar()
        self.menu.setNativeMenuBar(sys.platform != "Darwin")

        self.file_menu = self.menu.addMenu("&File")
        self.quit_action = self.file_menu.addAction("Quit", self.close)
        self.quit_action.setShortcut("Alt+F4")

        self.edit_menu = self.menu.addMenu("&Edit")

        self.settings_action = self.edit_menu.addAction("Settings", self.open_settings)
        self.settings_action.setShortcut("Ctrl+,")

        self.help_menu = self.menu.addMenu("&Help")

        self.about_action = self.help_menu.addAction("About", self.show_about)

        self.root_widget = QStackedWidget()
        self.setCentralWidget(self.root_widget)

        self.connection_form = ConnectionForm()
        self.connection_form.auth_pwd.connect(self.connect_pwd)
        self.connection_form.auth_key.connect(self.connect_key)
        self.root_widget.insertWidget(0, self.connection_form)

        self.connecting = ConnectingPage()
        self.root_widget.insertWidget(1, self.connecting)

        self.viewer = LogViewer(self.downloader)
        self.viewer.exited.connect(self.close_connection)
        self.root_widget.insertWidget(2, self.viewer)

    def apply_theme(self):
        theme_name = self.settings.value("theme", "Dark")
        if theme_name == "Dark":
            qta.dark(self.app)
            self.theme.set_style(ThemeStyle.Dark)
        elif theme_name == "Light":
            qta.light(self.app)
            self.theme.set_style(ThemeStyle.Light)
        else:
            self.theme.set_style(ThemeStyle.System)
            if self.theme.is_dark():
                qta.dark(self.app)
            else:
                qta.light(self.app)
        self.theme.apply(self)

    def open_settings(self):
        self.settings_window.show()

    def show_about(self):
        self.about_window.show()

    def request_host_key_option(self, policy: ConnectionWorker.HostKeyPolicy, hostname_str, _key_name, key_fingerprint):
        msg = QMessageBox.question(
            self,
            "Host Keys",
            f"Do you want to accept or deny the host key from {hostname_str}?\n{key_fingerprint}",
            QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Abort,
        )
        match msg:
            case QMessageBox.StandardButton.Open:
                policy.key_return = HostKeyOptionReturn.Accept
            case QMessageBox.StandardButton.Abort:
                policy.key_return = HostKeyOptionReturn.Abort

    def connect_pwd(self, host: str, port: int, user: str, password: str):
        self.root_widget.setCurrentIndex(1)

        self.connect_thread = QThread()
        self.connect_worker = ConnectionWorker(self.downloader, self)
        self.connect_worker.moveToThread(self.connect_thread)

        self.connect_worker.connected.connect(self.on_connected)
        self.connect_worker.connected.connect(self.connect_thread.quit)
        self.connect_worker.error.connect(self.connection_error)
        self.connect_worker.error.connect(self.connect_thread.quit)
        self.connect_worker.ask_host_key.connect(self.request_host_key_option)
        self.connect_thread.finished.connect(self.connect_thread.deleteLater)

        # Trigger `run_password()` inside the worker thread
        self.connect_thread.started.connect(lambda: self.connect_worker.start_password.emit(host, port, user, password))

        self.connect_thread.start()

    def connect_key(self, host: str, port: int, user: str, key: paramiko.RSAKey):
        self.root_widget.setCurrentIndex(1)

        self.connect_thread = QThread()
        self.connect_worker = ConnectionWorker(self.downloader, self)
        self.connect_worker.moveToThread(self.connect_thread)

        self.connect_worker.connected.connect(self.on_connected)
        self.connect_worker.connected.connect(self.connect_thread.quit)
        self.connect_worker.error.connect(self.connection_error)
        self.connect_worker.error.connect(self.connect_thread.quit)
        self.connect_worker.ask_host_key.connect(self.request_host_key_option)
        self.connect_thread.finished.connect(self.connect_thread.deleteLater)

        # Trigger `run_password()` inside the worker thread
        self.connect_thread.started.connect(lambda: self.connect_worker.start_key.emit(host, port, user, key))

        self.connect_thread.start()

    def connection_error(self, error: str):
        self.root_widget.setCurrentIndex(0)
        msg = QMessageBox(self)
        msg.setText(f"Connection failed: {error}")
        msg.setWindowTitle("Connection Error")
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.exec()

    @Slot()
    def on_connected(self):
        self.connect_thread.quit()
        self.logger.info("Connected successfully")
        self.root_widget.setCurrentIndex(2)
        self.viewer.populate()

    def close_connection(self):
        self.root_widget.setCurrentIndex(0)
        self.downloader.disconnect()


@dataclass
class LogDownloaderApplicationStartupArguments:
    verbose: bool = False
    trace: bool = True


class LogDownloaderApplicationRunner:
    def __init__(self, args: LogDownloaderApplicationStartupArguments | None = None):
        self.logger = Logger()

        setup_url_scheme()
        self.app = QApplication(sys.argv)

        self.configure_logger(args)

        self.logger.debug("Custom URL scheme set")

        self.app.setApplicationName("KevinbotLib Log Downloader")
        self.app.setApplicationVersion(__version__)
        self.app.setStyle("Fusion")  # can solve some platform-specific issues

        self.window = None

    def configure_logger(self, args: LogDownloaderApplicationStartupArguments | None):
        # this is needed on Windows when using --windowed in PyInstaller
        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w")  # noqa: SIM115
        if sys.stderr is None:
            sys.stderr = open(os.devnull, "w")  # noqa: SIM115

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
        kevinbotlib.apps.log_downloader.resources_rc.qInitResources()
        self.window = Application(self.app, self.logger)
        self.window.show()
        sys.exit(self.app.exec())


def execute(args: LogDownloaderApplicationStartupArguments | None):
    runner = LogDownloaderApplicationRunner(args)
    runner.run()


if __name__ == "__main__":
    execute(None)
