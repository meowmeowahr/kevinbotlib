import datetime
import html
import locale
import socket
from functools import partial

import orjson
import paramiko
from PySide6.QtCore import (
    QBuffer,
    QByteArray,
    QIODevice,
    QObject,
    QRunnable,
    Qt,
    QThread,
    QThreadPool,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWebEngineCore import QWebEngineUrlRequestJob, QWebEngineUrlScheme, QWebEngineUrlSchemeHandler
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from kevinbotlib.apps.common.widgets import QWidgetList
from kevinbotlib.apps.log_downloader.util import sizeof_fmt
from kevinbotlib.logger import Logger
from kevinbotlib.logger.downloader import RemoteLogDownloader
from kevinbotlib.logger.parser import Log, LogEntry

URL_SCHEME = "logdata"


class LogUrlSchemeHandler(QWebEngineUrlSchemeHandler):
    """URL scheme handler to serve large HTML content for logs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.html_data = {}

    def store_html(self, key: str, html: str):
        """Store HTML content for serving."""
        self.html_data[key] = html

    def requestStarted(self, job: QWebEngineUrlRequestJob):  # noqa: N802
        """Handle requests for our custom scheme."""
        path = job.requestUrl().path()

        if (data := self.html_data.get(path)) is not None:
            if not isinstance(data, bytes):
                data = str(data).encode("utf-8")

            mime = QByteArray(b"text/html")
            buffer = QBuffer(job)
            buffer.setData(data)
            buffer.open(QIODevice.OpenModeFlag.ReadOnly)
            job.reply(mime, buffer)
        else:
            Logger().error(f"ERROR: URL scheme request failed: {path!r}")
            job.fail(QWebEngineUrlRequestJob.Error.UrlNotFound)


def setup_url_scheme():
    """Register the custom URL scheme. MUST be called before QApplication creation!"""
    scheme = QWebEngineUrlScheme(bytes(URL_SCHEME, "ascii"))
    scheme.setFlags(
        QWebEngineUrlScheme.Flag.SecureScheme
        | QWebEngineUrlScheme.Flag.LocalScheme
        | QWebEngineUrlScheme.Flag.LocalAccessAllowed
    )
    QWebEngineUrlScheme.registerScheme(scheme)


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

            log = self.downloader.get_log(
                self.logfile,
                progress_callback=lambda p: self.signals.progress.emit(p) if not self.is_cancelled else None,
            )
            if not self.is_cancelled:
                self.signals.finished.emit(log)
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

    def cancel(self):
        self.is_cancelled = True


class LogEntryWidget:
    def __init__(self, entry: LogEntry, parent: QObject | None = None):
        self.parent = parent
        self.entry = entry

    def get_level_color(self):
        colors = {
            "TRACE": QColor(16, 80, 96),  # Dark teal
            "DEBUG": QColor(16, 64, 96),  # Dark blue
            "INFO": QColor(128, 128, 128),  # Gray
            "WARNING": QColor(96, 80, 16),  # Dark yellow
            "ERROR": QColor(96, 16, 16),  # Dark red
            "SECURITY": QColor(96, 58, 16),  # Dark orange
            "CRITICAL": QColor(96, 16, 96),  # Dark purple
        }
        color = colors.get(self.entry.level_name, QColor(128, 128, 128))  # Default gray
        return color.name(QColor.NameFormat.HexRgb) + "55"  # Returns color in #AARRGGBB format

    def get_subtext_color(self):
        if self.parent:
            palette = self.parent.palette()
            return palette.color(QPalette.ColorRole.Text).name()
        return "#333333"  # Fallback dark gray for text

    def get_text_color(self):
        if self.parent:
            palette = self.parent.palette()
            text_color = palette.color(QPalette.ColorRole.Text)
            # Lighten the text color slightly for subtext
            text_color = text_color.lighter(150)
            return text_color.name()
        return "#666666"  # Fallback medium gray for subtext

    def get_border_color(self):
        color = self.get_level_color()
        return color[:-2]

    def get_html(self):
        text_color = self.get_text_color()
        subtext_color = self.get_subtext_color()
        bg_color = self.get_level_color()
        border_color = self.get_border_color()

        return f"""
        <table width="100%" style="margin: 8px 0; border Ascending: true; border: 2px solid {border_color}; border-radius: 6px; background-color: {bg_color};">
            <tr>
                <td style="padding: 12px;">
                    <div style="color: {subtext_color}; font-size: 11pt; font-family: sans-serif; margin-bottom: 6px;">
                        {self.entry.level_name} - {self.entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")} - {self.entry.modname}.{self.entry.function}:{self.entry.line}
                    </div>
                    <div style="color: {text_color}; font-size: 13pt; font-family: monospace; white-space: pre-wrap;">{html.escape(self.entry.message.strip("\n\r "))}</div>
                </td>
            </tr>
        </table>
        """


class LogPanel(QStackedWidget):
    def __init__(self, downloader: RemoteLogDownloader):
        super().__init__()
        self.downloader = downloader
        self.thread_pool = QThreadPool.globalInstance()
        self.current_worker = None  # Track the current worker for cancellation

        self.loading_widget = QWidget()
        self.insertWidget(0, self.loading_widget)

        self.progress_layout = QVBoxLayout()
        self.loading_widget.setLayout(self.progress_layout)

        self.progress_layout.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_layout.addWidget(self.progress_bar)

        self.loading_label = QLabel("Please Wait...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.progress_layout.addWidget(self.loading_label)

        self.progress_layout.addStretch()

        # Create web view with URL scheme handler
        self.text_area = QWebEngineView()
        self.text_area.setStyleSheet("background-color: transparent;")
        self.text_area.page().setBackgroundColor(QColor(0, 0, 0, 0))
        self.text_area.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.text_area.setHtml("Please wait...")
        self.url_handler = LogUrlSchemeHandler(self)
        self.text_area.page().profile().installUrlSchemeHandler(bytes(URL_SCHEME, "ascii"), self.url_handler)

        # Handle load failures gracefully
        self.text_area.loadFinished.connect(self.handle_load_finished)

        self.insertWidget(1, self.text_area)

        # Assuming these are defined in QWidgetList
        self.set_loading(True)
        self.progress_bar.hide()
        self.loading_label.setText("Select a Log File")

    def handle_load_finished(self, ok: bool):
        """Handle case where URL scheme loading fails."""
        if not ok:
            Logger().error("URL scheme loading failed, content might be too large")
            # Could show an error message in the web view
            self.text_area.setHtml("<h3>Error: Failed to load log content</h3>")

    def set_loading(self, loading: bool):
        """Show or hide the loading/progress screen."""
        if loading:
            self.setCurrentWidget(self.loading_widget)
        else:
            self.setCurrentWidget(self.text_area)

    def set_progress(self, value: int, text: str = ""):
        """Update progress bar value and optional text."""
        self.progress_bar.setValue(value)
        if text:
            self.loading_label.setText(text)

    def load(self, name: str):
        # Cancel any existing task
        if self.thread_pool.activeThreadCount() > 0:
            QMessageBox.warning(
                self,
                "Another Operation Running",
                "Another operation is already running. Please wait before attempting to load another log file.",
                QMessageBox.StandardButton.Ok,
            )
            return

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
        """Update the UI with the loaded log data using URL scheme handler."""
        self.set_loading(False)
        self.progress_bar.hide()
        self.loading_label.setText("Log Loaded")
        self.current_worker = None

        # Generate HTML content
        html = '<meta charset="UTF-8">\n'
        for item in log:
            widget = LogEntryWidget(item, self)
            html += widget.get_html() + "\n"

        # Store HTML in the URL scheme handler
        log_key = f"/log_{id(log)}"  # Use unique key based on log object id
        self.url_handler.store_html(log_key, html)

        # Load using custom URL scheme
        url = QUrl(log_key)
        url.setScheme(URL_SCHEME)
        self.text_area.setUrl(url)

    def handle_error(self, error: str):
        """Handle errors from the worker."""
        self.set_loading(False)
        self.progress_bar.hide()
        self.loading_label.setText(f"Error: {error}")
        self.text_area.setHtml(
            f"<h3 style='font-family: sans-serif; color: #ef1010;'>Error: Failed to load log content: {error}</h3>"
        )
        self.current_worker = None


class LogViewer(QSplitter):
    def __init__(self, downloader: RemoteLogDownloader, parent=None):
        super().__init__(parent)
        self.setContentsMargins(2, 2, 2, 2)
        
        self.thread_pool = QThreadPool.globalInstance()

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
        self.populate_worker.finished.connect(
            lambda: self.sidebar_browse.set_loading(False)
        )
        self.populate_worker.progress.connect(self.sidebar_browse.set_progress)

        # Start worker in thread pool
        QThreadPool.globalInstance().start(self.populate_worker.run)

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
