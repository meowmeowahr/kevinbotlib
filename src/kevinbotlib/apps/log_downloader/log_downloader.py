import sys
from dataclasses import dataclass

from PySide6.QtCore import QCommandLineParser, QCommandLineOption, QCoreApplication
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow

import kevinbotlib.apps.log_downloader.resources_rc
from kevinbotlib.__about__ import __version__
from kevinbotlib.logger import Logger, Level, LoggerConfiguration


class Application(QMainWindow):
    def __init__(self, app: QApplication, logger: Logger):
        super().__init__()
        self.setWindowIcon(QIcon(":/app_icons/log-downloader-small.svg"))

@dataclass
class LogDownloaderApplicationStartupArguments:
    verbose: bool = False
    trace: bool = True


class LogDownloaderApplicationRunner:
    def __init__(self, args: LogDownloaderApplicationStartupArguments | None = None):
        self.logger = Logger()
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("KevinbotLib Log Downloader")
        self.app.setApplicationVersion(__version__)
        self.app.setStyle("Fusion")  # can solve some platform-specific issues

        self.configure_logger(args)
        self.window = None

    def configure_logger(self, args: LogDownloaderApplicationStartupArguments | None):
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
