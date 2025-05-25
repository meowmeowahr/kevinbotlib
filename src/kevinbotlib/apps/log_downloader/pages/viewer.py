import datetime
import locale
import socket
from functools import partial

import orjson
import paramiko
import qtawesome as qta
from PySide6.QtCore import (
    QObject,
    QRunnable,
    QSize,
    Qt,
    QThreadPool,
    Signal,
    Slot,
)
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from kevinbotlib.apps.common.widgets import QWidgetList
from kevinbotlib.apps.log_downloader.log_panel import LogPanel
from kevinbotlib.apps.log_downloader.util import sizeof_fmt
from kevinbotlib.logger.downloader import RemoteLogDownloader


class PopulateWorker(QObject):
    finished = Signal(list)
    progress = Signal(int)
    start = Signal()

    def __init__(self, downloader: RemoteLogDownloader):
        super().__init__()
        self.downloader = downloader
        self.start.connect(self.run)

    @Slot()
    def run(self):
        out = []
        self.progress.emit(0)
        files = self.downloader.get_logfiles()

        # get metadata
        for i, f in enumerate(files):
            mod_time = self.downloader.get_file_modification_time(f)
            size = self.downloader.get_file_size(f)
            out.append({"name": f, "mod_time": mod_time, "size": size})
            self.progress.emit(i / len(files) * 100)

        self.progress.emit(100)
        self.finished.emit(out)


class LogDeleteWorkerSignals(QObject):
    finished = Signal(str)
    error = Signal(str)


class LogDeleteWorker(QRunnable):
    def __init__(self, downloader: RemoteLogDownloader, logfile: str):
        super().__init__()
        self.downloader = downloader
        self.logfile = logfile
        self.signals = LogDeleteWorkerSignals()
        self.is_cancelled = False
        self.setAutoDelete(True)

    def run(self):
        if self.is_cancelled:
            return
        try:
            self.downloader.delete_log(self.logfile)
        except paramiko.AuthenticationException:
            self.signals.error.emit("Authentication failed")
            return
        except TimeoutError:
            self.signals.error.emit("Connection timed out")
            return
        except socket.gaierror as e:
            self.signals.error.emit(f"Could not resolve hostname: {e!r}")
            return
        except orjson.JSONDecodeError as e:
            self.signals.error.emit(f"Could not decode log: {e!r}")
            return
        self.signals.finished.emit(self.logfile)


class LogFileWidget(QFrame):
    clicked = Signal()
    deleted = Signal()

    def __init__(self, name: str, mod_time: datetime.datetime, size: str, parent=None):
        super().__init__(parent)
        self.name = name
        self.mod_time = mod_time
        self.size = size

        self.root_layout = QHBoxLayout()
        self.setLayout(self.root_layout)

        self.info_layout = QVBoxLayout()
        self.root_layout.addLayout(self.info_layout)

        self.name_label = QLabel(name)
        self.name_label.setFont(QFont(self.font().family(), 12))
        self.info_layout.addWidget(self.name_label)

        self.mod_time_label = QLabel("Modified at: " + mod_time.strftime(locale.nl_langinfo(locale.D_T_FMT)))
        self.mod_time_label.setFont(QFont(self.font().family(), 10))
        self.info_layout.addWidget(self.mod_time_label)

        self.size_label = QLabel(f"File Size: {sizeof_fmt(size)}")
        self.size_label.setFont(QFont(self.font().family(), 10))
        self.info_layout.addWidget(self.size_label)

        self.root_layout.addStretch()

        self.delete_button = QPushButton()
        self.delete_button.setIcon(qta.icon("mdi6.delete-forever", color="#d45b5a"))
        self.delete_button.setIconSize(QSize(24, 24))
        self.delete_button.setFixedSize(QSize(32, 32))
        self.delete_button.clicked.connect(self.deleted.emit)
        self.root_layout.addWidget(self.delete_button)

        self.setFrameShape(QFrame.Shape.Panel)
        self.setFixedHeight(self.sizeHint().height() + 2)

    def mouseReleaseEvent(self, _event):  # noqa: N802
        self.clicked.emit()


class LogViewer(QWidget):
    exited = Signal()

    def __init__(self, downloader: RemoteLogDownloader, parent=None):
        super().__init__(parent)
        self.setContentsMargins(2, 2, 2, 2)

        self.root_layout = QVBoxLayout()
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.root_layout)

        self.toolbar = QToolBar()
        self.root_layout.addWidget(self.toolbar)

        self.close_connection_action = QAction(qta.icon("mdi6.exit-run", color="#d45b5a"), "Close Connection", self)
        self.close_connection_action.triggered.connect(self.exit)
        self.toolbar.addAction(self.close_connection_action)

        self.reload_action = QAction(qta.icon("mdi6.refresh", color="#c9c95a"), "Reload", self)
        self.reload_action.triggered.connect(self.reload)
        self.toolbar.addAction(self.reload_action)

        self.thread_pool = QThreadPool.globalInstance()
        self.populate_worker = None

        self.downloader = downloader

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.root_layout.addWidget(self.splitter)

        self.sidebar_widget = QWidget()
        self.splitter.addWidget(self.sidebar_widget)

        self.sidebar_layout = QVBoxLayout()
        self.sidebar_widget.setLayout(self.sidebar_layout)

        self.sidebar_browse = QWidgetList()
        self.sidebar_browse.set_loading(True)
        self.sidebar_browse.set_spacing(4)
        self.sidebar_layout.addWidget(self.sidebar_browse)

        self.log_panel = LogPanel(self.downloader)
        self.splitter.addWidget(self.log_panel)

    def exit(self):
        self.sidebar_browse.clear_widgets()
        self.log_panel.close_log()
        self.sidebar_browse.set_loading(True)
        self.exited.emit()

    def populate(self):
        if self.thread_pool.activeThreadCount() > 0:
            QMessageBox.warning(
                self,
                "Another Operation Running",
                "Another operation is already running. Please wait before attempting to load another log file.",
                QMessageBox.StandardButton.Ok,
            )
            return

        # Create new worker
        self.populate_worker = PopulateWorker(self.downloader)
        self.populate_worker.finished.connect(self.set_items)
        self.populate_worker.finished.connect(lambda: self.sidebar_browse.set_loading(False))
        self.populate_worker.progress.connect(self.sidebar_browse.set_progress)

        # Start worker in thread pool
        QThreadPool.globalInstance().start(self.populate_worker.run)

    def set_items(self, items: list):
        items.sort(key=lambda i: i["name"], reverse=True)
        for item in items:
            widget = LogFileWidget(item["name"], item["mod_time"], item["size"], parent=self.sidebar_browse)
            widget.clicked.connect(partial(self.load_log, item["name"]))
            widget.deleted.connect(partial(self.delete_log, item["name"]))
            self.sidebar_browse.add_widget(widget)
        self.sidebar_browse.set_loading(False)

    def delete_log(self, logfile: str):
        if self.thread_pool.activeThreadCount() > 0:
            QMessageBox.warning(
                self,
                "Another Operation Running",
                "Another operation is already running. Please wait before attempting to load another log file.",
                QMessageBox.StandardButton.Ok,
            )
            return

        worker = LogDeleteWorker(self.downloader, logfile)
        worker.signals.finished.connect(self.reload)
        worker.signals.error.connect(lambda e: QMessageBox.critical(self, "Error", f"Error deleting log: {e}"))
        self.thread_pool.start(worker)

    def reload(self):
        self.sidebar_browse.clear_widgets()
        self.sidebar_browse.set_loading(True)
        self.populate()

    def load_log(self, name: str):
        self.log_panel.load_remote(name)
