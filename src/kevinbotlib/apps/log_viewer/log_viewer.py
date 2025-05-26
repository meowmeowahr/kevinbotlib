import os
import sys
from dataclasses import dataclass

import qtawesome as qta
from PySide6.QtCore import (
    QCommandLineOption,
    QCommandLineParser,
    QCoreApplication,
    QSettings,
    Signal,
)
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
)

import kevinbotlib.apps.log_viewer.resources_rc
from kevinbotlib.__about__ import __version__
from kevinbotlib.apps.common.abc import ThemableWindow
from kevinbotlib.apps.common.about import AboutDialog
from kevinbotlib.apps.common.settings_rows import Divider, UiColorSettingsSwitcher
from kevinbotlib.apps.common.toast import NotificationWidget, Severity
from kevinbotlib.apps.common.url_scheme import setup_url_scheme
from kevinbotlib.apps.log_viewer.log_panel import LogPanel
from kevinbotlib.apps.log_viewer.pages.upload import UploadForm
from kevinbotlib.logger import Level, Logger, LoggerConfiguration
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


class Application(ThemableWindow):
    def __init__(self, app: QApplication, logger: Logger):
        super().__init__()
        self.app = app
        self.logger = logger

        self.connect_worker = None
        self.connect_thread = None

        self.setWindowIcon(QIcon(":/app_icons/log-viewer-small.svg"))
        self.setWindowIcon(QIcon(":/app_icons/log-viewer-small.svg"))

        self.settings = QSettings("kevinbotlib", "logviewer")
        self.theme = Theme(ThemeStyle.System)
        self.apply_theme()

        self.settings_window = SettingsWindow(self, self.settings)

        self.about_window = AboutDialog(
            "KevinbotLib Log Viewer",
            "View Locally Stored Logs from a KevinbotLib Robot",
            __version__,
            "\nSource code is licensed under the GNU LGPLv3\nBinaries are licensed under the GNU GPLv3 due to some GPL components\nSee 'Open Source Licenses' for more details...",
            QIcon(":/app_icons/log-viewer.svg"),
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

        self.connection_form = UploadForm()
        self.connection_form.load_file_path.connect(self.load)
        self.root_widget.insertWidget(0, self.connection_form)

        self.panel = LogPanel()
        self.panel.closed.connect(lambda: self.root_widget.setCurrentIndex(0))
        self.root_widget.insertWidget(1, self.panel)

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

    def load(self, path: str):
        self.root_widget.setCurrentIndex(1)
        self.panel.load_local(path)


@dataclass
class LogViewerApplicationStartupArguments:
    verbose: bool = False
    trace: bool = True


class LogViewerApplicationRunner:
    def __init__(self, args: LogViewerApplicationStartupArguments | None = None):
        self.logger = Logger()

        setup_url_scheme()
        self.app = QApplication(sys.argv)

        self.configure_logger(args)

        self.logger.debug("Custom URL scheme set")

        self.app.setApplicationName("KevinbotLib Log Viewer")
        self.app.setApplicationVersion(__version__)
        self.app.setStyle("Fusion")  # can solve some platform-specific issues

        self.window = None

    def configure_logger(self, args: LogViewerApplicationStartupArguments | None):
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
        kevinbotlib.apps.log_viewer.resources_rc.qInitResources()
        self.window = Application(self.app, self.logger)
        self.window.show()
        sys.exit(self.app.exec())


def execute(args: LogViewerApplicationStartupArguments | None):
    runner = LogViewerApplicationRunner(args)
    runner.run()


if __name__ == "__main__":
    execute(None)
