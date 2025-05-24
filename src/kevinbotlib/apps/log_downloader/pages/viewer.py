import datetime
import locale
from functools import partial

from PySide6.QtWidgets import QTextEdit
from PySide6.QtCore import QObject, QThread, Signal, Slot, QRunnable, QThreadPool
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSplitter, QVBoxLayout, QWidget

from kevinbotlib.apps.common.widgets import QWidgetList
from kevinbotlib.apps.log_downloader.util import sizeof_fmt
from kevinbotlib.logger.downloader import RemoteLogDownloader
from kevinbotlib.logger.parser import Log, LogEntry


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

class LogFileWidget(QFrame):
    clicked = Signal()

    def __init__(self, name: str, mod_time: datetime.datetime, size: str, parent=None):
        super().__init__(parent)
        self.name = name
        self.mod_time = mod_time
        self.size = size

        self.root_layout = QVBoxLayout()
        self.setLayout(self.root_layout)

        self.name_label = QLabel(name)
        self.name_label.setFont(QFont(self.font().family(), 12))
        self.root_layout.addWidget(self.name_label)

        self.mod_time_label = QLabel("Modified at: " + mod_time.strftime(locale.nl_langinfo(locale.D_T_FMT)))
        self.mod_time_label.setFont(QFont(self.font().family(), 10))
        self.root_layout.addWidget(self.mod_time_label)

        self.size_label = QLabel(f"File Size: {sizeof_fmt(size)}")
        self.size_label.setFont(QFont(self.font().family(), 10))
        self.root_layout.addWidget(self.size_label)

        self.setFrameShape(QFrame.Shape.Panel)
        self.setFixedHeight(self.sizeHint().height() + 2)

    def mouseReleaseEvent(self, _event):  # noqa: N802
        self.clicked.emit()


class LogFetchWorkerSignals(QObject):
    """Signal class for LogFetchWorker to emit progress and results."""
    progress = Signal(float)
    finished = Signal(Log)
    error = Signal(str)

class LogFetchWorker(QRunnable):
    """Worker class to fetch a log file in a thread pool."""
    def __init__(self, downloader: RemoteLogDownloader, logfile: str):
        super().__init__()
        self.downloader = downloader
        self.logfile = logfile
        self.signals = LogFetchWorkerSignals()
        self.is_cancelled = False
        self.setAutoDelete(True)  # Let QThreadPool manage worker deletion

    def run(self):
        try:
            if self.is_cancelled:
                return

            # Download the log with progress callback
            log = self.downloader.get_log(
                self.logfile,
                progress_callback=lambda p: self.signals.progress.emit(p) if not self.is_cancelled else None
            )
            if not self.is_cancelled:
                self.signals.finished.emit(log)
        except Exception as e:
            if not self.is_cancelled:
                self.signals.error.emit(str(e))

    def cancel(self):
        self.is_cancelled = True

class LogEntryWidget(QFrame):
    def __init__(self, entry: LogEntry):
        super().__init__()
        self.entry = entry
        self.root_layout = QHBoxLayout()
        self.setLayout(self.root_layout)

        self.log_text = QTextEdit(readOnly=True)
        self.log_text.setStyleSheet("border: none; background-color: transparent;")
        self.log_text.setFrameStyle(QFrame.Shape.NoFrame)
        self.log_text.setPlainText(self.entry.message)
        self.root_layout.addWidget(self.log_text)

        # TODO: Add timestamp, icon, color background based on level, etc...

class LogPanel(QWidgetList):
    def __init__(self, downloader: RemoteLogDownloader):
        super().__init__()
        self.downloader = downloader
        self.thread_pool = QThreadPool.globalInstance()
        self.current_worker = None  # Track the current worker for cancellation

        # Assuming these are defined in QWidgetList
        self.set_loading(True)
        self.set_spacing(4)
        self.progress_bar.hide()
        self.loading_label.setText("Select a Log File")

    def load(self, name: str):
        # Cancel any existing task
        if self.current_worker:
            self.current_worker.cancel()
            self.thread_pool.tryTake(self.current_worker)
            self.current_worker = None

        self.clear_widgets()
        self.set_loading(True)
        self.loading_label.setText(f"Loading {name}...")
        self.progress_bar.show()
        self.progress_bar.setValue(0)

        # Create and start the worker
        self.current_worker = LogFetchWorker(self.downloader, name)
        self.current_worker.signals.progress.connect(self.progress_bar.setValue)
        self.current_worker.signals.finished.connect(self.set_items)
        self.current_worker.signals.error.connect(self.handle_error)

        self.thread_pool.start(self.current_worker)

    def set_items(self, log: Log):
        """Update the UI with the loaded log data."""
        self.set_loading(False)
        self.progress_bar.hide()
        self.loading_label.setText("Log Loaded")
        self.current_worker = None
        for item in log:
            widget = LogEntryWidget(item)
            self.add_widget(widget)


    def handle_error(self, error: str):
        """Handle errors from the worker."""
        self.set_loading(False)
        self.progress_bar.hide()
        self.loading_label.setText(f"Error: {error}")
        self.current_worker = None

class LogViewer(QSplitter):
    def __init__(self, downloader: RemoteLogDownloader, parent=None):
        super().__init__(parent)
        self.setContentsMargins(2, 2, 2, 2)

        self.downloader = downloader

        self.populate_thread = None
        self.populate_worker = None

        self.sidebar_widget = QWidget()
        self.addWidget(self.sidebar_widget)

        self.sidebar_layout = QVBoxLayout()
        self.sidebar_widget.setLayout(self.sidebar_layout)

        self.sidebar_topbar = QHBoxLayout()
        self.sidebar_topbar.addStretch()
        self.sidebar_layout.addLayout(self.sidebar_topbar)

        self.reload_button = QPushButton("Reload")
        self.reload_button.clicked.connect(self.reload)
        self.sidebar_topbar.addWidget(self.reload_button)

        self.sidebar_browse = QWidgetList()
        self.sidebar_browse.set_loading(True)
        self.sidebar_browse.set_spacing(4)
        self.sidebar_layout.addWidget(self.sidebar_browse)

        self.log_panel = LogPanel(self.downloader)
        self.addWidget(self.log_panel)

    def populate(self):
        self.populate_thread = QThread()
        self.populate_worker = PopulateWorker(self.downloader)
        self.populate_worker.moveToThread(self.populate_thread)

        # Connect worker's finished/updates to UI methods
        self.populate_worker.finished.connect(self.set_items)
        self.populate_worker.finished.connect(lambda: self.sidebar_browse.set_loading(False))
        self.populate_worker.progress.connect(self.sidebar_browse.set_progress)

        # Trigger run() via signal (runs in thread)
        self.populate_thread.started.connect(self.populate_worker.start.emit)

        # Clean up
        self.populate_worker.finished.connect(self.populate_thread.quit)
        self.populate_thread.finished.connect(self.populate_thread.deleteLater)

        self.populate_thread.start()

    def set_items(self, items: list):
        for item in items:
            widget = LogFileWidget(item["name"], item["mod_time"], item["size"], parent=self.sidebar_browse)
            widget.clicked.connect(partial(self.load_log, item["name"]))
            self.sidebar_browse.add_widget(widget)
        self.sidebar_browse.set_loading(False)

    def reload(self):
        self.sidebar_browse.clear_widgets()
        self.sidebar_browse.set_loading(True)
        self.populate()

    def load_log(self, name: str):
        self.log_panel.load(name)
