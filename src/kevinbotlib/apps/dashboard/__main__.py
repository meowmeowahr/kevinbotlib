# SPDX-FileCopyrightText: 2025-present meowmeowahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: LGPL-3.0-or-later

import sys

from kevinbotlib.logger import Level, Logger, LoggerConfiguration
from PySide6.QtCore import QCommandLineOption, QCommandLineParser, QCoreApplication
from PySide6.QtWidgets import QApplication

from kevinbotlib import __about__
from kevinbotlib.apps.dashboard.app import Application


def run():
    app = QApplication(sys.argv)
    app.setApplicationName("KevinbotLib Dashboard")
    app.setApplicationVersion(__about__.__version__)

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

    window = Application(app)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
