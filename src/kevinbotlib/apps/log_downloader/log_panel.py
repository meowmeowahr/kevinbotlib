import html
import socket

import orjson
import paramiko
import qtawesome as qta
from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, QUrl, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from kevinbotlib.apps.common.url_scheme import URL_SCHEME, LogUrlSchemeHandler
from kevinbotlib.apps.common.webfind import FindDialog
from kevinbotlib.logger import Logger
from kevinbotlib.logger.downloader import RemoteLogDownloader
from kevinbotlib.logger.parser import Log, LogEntry, LogParser


class LogEntryWidget:
    def __init__(self, entry: LogEntry, palette: QPalette, text_color: str, subtext_color: str):
        self.palette = palette
        self.text_color = text_color
        self.subtext_color = subtext_color
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

    def get_border_color(self):
        color = self.get_level_color()
        return color[:-2]

    def get_html(self):
        text_color = self.text_color
        subtext_color = self.subtext_color
        bg_color = self.get_level_color()
        border_color = self.get_border_color()

        return f"""
        <table width="100%" style="margin: 8px 0; border Ascending: true; border: 2px solid {border_color}; border-radius: 6px; background-color: {bg_color};">
            <tr>
                <td style="padding: 8px;">
                    <div style="color: {subtext_color}; font-size: 10pt; font-family: sans-serif; margin-bottom: 6px;">
                        {self.entry.level_name} - {self.entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")} - {self.entry.modname}.{self.entry.function}:{self.entry.line}
                    </div>
                    <div style="color: {text_color}; font-size: 11pt; font-family: monospace; white-space: pre-wrap;">{html.escape(self.entry.message.strip("\n\r "))}</div>
                </td>
            </tr>
        </table>
        """


class LogFetchWorkerSignals(QObject):
    """Signal class for LogFetchWorker to emit progress and results."""

    progress = Signal(float)
    finished = Signal(Log, str, str)
    error = Signal(str)


class LogFetchWorker(QRunnable):
    """Worker class to fetch a log file in a thread pool."""

    def __init__(self, downloader: RemoteLogDownloader, logfile: str, palette: QPalette):
        super().__init__()
        self.downloader = downloader
        self.palette = palette
        self.logfile = logfile
        self.signals = LogFetchWorkerSignals()
        self.is_cancelled = False
        self.setAutoDelete(True)  # Let QThreadPool manage worker deletion

    def run(self):
        try:
            if self.is_cancelled:
                return

            raw = self.downloader.get_raw_log(
                self.logfile,
                progress_callback=lambda p: self.signals.progress.emit(p / 2) if not self.is_cancelled else None,
            )
            log = LogParser.parse(raw)
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

        # Generate HTML content
        html_data = '<meta charset="UTF-8">\n'

        palette = self.palette

        text_color = self.palette.color(QPalette.ColorRole.Text)
        # Lighten the text color slightly for subtext
        text_color = text_color.lighter(150)
        text_color = text_color.name()

        subtext_color = self.palette.color(QPalette.ColorRole.Text).name()

        total = len(log)
        for i, item in enumerate(log):
            widget = LogEntryWidget(item, palette, text_color, subtext_color)
            html_data += widget.get_html() + "\n"
            self.signals.progress.emit((i / total * 50) + 50)
            if self.is_cancelled:
                break

        if not self.is_cancelled:
            self.signals.finished.emit(html_data, raw, self.logfile.rsplit(".", maxsplit=1)[0])

    def cancel(self):
        self.is_cancelled = True


class LogPanel(QStackedWidget):
    def __init__(self, downloader: RemoteLogDownloader):
        super().__init__()
        self.downloader = downloader
        self.thread_pool = QThreadPool.globalInstance()
        self.current_worker = None  # Track the current worker for cancellation

        self.current_raw_log = None
        self.current_log_name = None

        self.loading_widget = QWidget()
        self.insertWidget(0, self.loading_widget)

        self.progress_layout = QVBoxLayout()
        self.loading_widget.setLayout(self.progress_layout)

        self.progress_layout.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_layout.addWidget(self.progress_bar)

        self.loading_label = QLabel("Please Wait...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.progress_layout.addWidget(self.loading_label)

        self.progress_layout.addStretch()

        self.viewer_widget = QWidget()
        self.insertWidget(1, self.viewer_widget)

        self.viewer_layout = QVBoxLayout()
        self.viewer_widget.setLayout(self.viewer_layout)

        self.viewer_bar_layout = QHBoxLayout()
        self.viewer_layout.addLayout(self.viewer_bar_layout)

        self.viewer_file_label = QLabel("Select a Log File")
        self.viewer_file_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.viewer_bar_layout.addWidget(self.viewer_file_label)

        self.find_button = QPushButton()
        self.find_button.setIcon(qta.icon("mdi6.file-find"))
        self.find_button.setIconSize(QSize(24, 24))
        self.find_button.setFixedSize(QSize(32, 32))
        self.find_button.clicked.connect(self.show_find_dialog)
        self.viewer_bar_layout.addWidget(self.find_button)

        self.log_zoom_in_button = QPushButton()
        self.log_zoom_in_button.setIcon(qta.icon("mdi6.magnify-plus"))
        self.log_zoom_in_button.setIconSize(QSize(24, 24))
        self.log_zoom_in_button.setFixedSize(QSize(32, 32))
        self.log_zoom_in_button.clicked.connect(lambda: self.text_area.setZoomFactor(self.text_area.zoomFactor() + 0.1))
        self.viewer_bar_layout.addWidget(self.log_zoom_in_button)

        self.log_zoom_reset_button = QPushButton()
        self.log_zoom_reset_button.setIcon(qta.icon("mdi6.magnify-close"))
        self.log_zoom_reset_button.setIconSize(QSize(24, 24))
        self.log_zoom_reset_button.setFixedSize(QSize(32, 32))
        self.log_zoom_reset_button.clicked.connect(lambda: self.text_area.setZoomFactor(1))
        self.viewer_bar_layout.addWidget(self.log_zoom_reset_button)

        self.log_zoom_out_button = QPushButton()
        self.log_zoom_out_button.setIcon(qta.icon("mdi6.magnify-minus"))
        self.log_zoom_out_button.setIconSize(QSize(24, 24))
        self.log_zoom_out_button.setFixedSize(QSize(32, 32))
        self.log_zoom_out_button.clicked.connect(
            lambda: self.text_area.setZoomFactor(self.text_area.zoomFactor() - 0.1)
        )
        self.viewer_bar_layout.addWidget(self.log_zoom_out_button)

        self.log_download_button = QPushButton()
        self.log_download_button.setIcon(qta.icon("mdi6.download", color="#5ac95a"))
        self.log_download_button.setIconSize(QSize(24, 24))
        self.log_download_button.setFixedSize(QSize(32, 32))
        self.log_download_button.clicked.connect(self.download_log)
        self.viewer_bar_layout.addWidget(self.log_download_button)

        self.log_close_button = QPushButton()
        self.log_close_button.setIcon(qta.icon("mdi6.close", color="#d45b5a"))
        self.log_close_button.setIconSize(QSize(24, 24))
        self.log_close_button.setFixedSize(QSize(32, 32))
        self.log_close_button.clicked.connect(self.close_log)
        self.viewer_bar_layout.addWidget(self.log_close_button)

        self.text_area = QWebEngineView()
        self.text_area.setStyleSheet("background-color: transparent;")
        self.text_area.settings().setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, False)
        self.text_area.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, False)
        self.text_area.settings().setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, False)
        self.text_area.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, False)
        self.text_area.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, False)
        self.text_area.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        self.text_area.page().setBackgroundColor(QColor(0, 0, 0, 0))
        self.text_area.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.text_area.setHtml("Please wait...")
        self.url_handler = LogUrlSchemeHandler(self)
        self.text_area.page().profile().installUrlSchemeHandler(bytes(URL_SCHEME, "ascii"), self.url_handler)
        self.viewer_layout.addWidget(self.text_area)
        self.text_area.loadFinished.connect(self.handle_load_finished)

        self.find_dialog = FindDialog(self.text_area, self)

        self.set_loading(True)
        self.progress_bar.hide()
        self.loading_label.setText("Select a Log File")

    def show_find_dialog(self):
        self.find_dialog.show()
        self.find_dialog.find_input.setFocus()

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
            self.setCurrentWidget(self.viewer_widget)

    def set_progress(self, value: int, text: str = ""):
        """Update progress bar value and optional text."""
        self.progress_bar.setValue(value)
        if text:
            self.loading_label.setText(text)

    def load_remote(self, name: str):
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
        self.viewer_file_label.setText(f"Selected Log: {name}")
        self.progress_bar.show()
        self.progress_bar.setValue(0)

        # Create and start the worker
        self.current_worker = LogFetchWorker(self.downloader, name, self.palette())
        self.current_worker.signals.progress.connect(self.progress_bar.setValue)
        self.current_worker.signals.finished.connect(self.set_items)
        self.current_worker.signals.error.connect(self.handle_error)

        self.thread_pool.start(self.current_worker)

    def set_items(self, log: str, raw: str, name: str):
        """Update the UI with the loaded log data using URL scheme handler."""
        self.current_raw_log = raw
        self.current_log_name = name
        self.set_loading(False)
        self.progress_bar.hide()
        self.loading_label.setText("Log Loaded")
        self.current_worker = None

        log_key = f"/log_{id(log)}"
        self.url_handler.store_html(log)

        url = QUrl(log_key)
        url.setScheme(URL_SCHEME)
        self.text_area.setUrl(url)

    def close_log(self):
        self.set_loading(True)
        self.progress_bar.hide()
        self.loading_label.setText("Log Closed")
        self.current_worker = None
        self.viewer_file_label.setText("Select a Log File")
        self.text_area.setHtml("Please wait...")

    def download_log(self):
        if self.current_raw_log is None:
            QMessageBox.warning(
                self,
                "No Log Selected",
                "Please select a log file before attempting to download it.",
                QMessageBox.StandardButton.Ok,
            )
            return

        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setNameFilter("Log Files (*.log)")
        dialog.setWindowTitle("Download Log")
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)

        if self.current_log_name:
            dialog.selectFile(self.current_log_name)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            filename = dialog.selectedFiles()[0]
            if not filename.endswith(".log"):
                filename += ".log"

            with open(filename, "w") as f:
                f.write(self.current_raw_log)

    def handle_error(self, error: str):
        """Handle errors from the worker."""
        self.set_loading(False)
        self.progress_bar.hide()
        self.loading_label.setText(f"Error: {error}")
        self.text_area.setHtml(
            f"<h3 style='font-family: sans-serif; color: #ef1010;'>Error: Failed to load log content: {error}</h3>"
        )
        self.current_worker = None
