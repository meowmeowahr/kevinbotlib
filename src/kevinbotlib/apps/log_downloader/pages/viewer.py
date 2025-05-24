from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import QThread, Signal, Slot, QObject

from kevinbotlib.apps.common.widgets import QWidgetList
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
            mtime = self.downloader.get_file_modification_time(f)
            out.append({"name": f, "mtime": mtime})
            self.progress.emit(i / len(files) * 100)

        self.progress.emit(100)
        self.finished.emit(out)


class LogViewer(QSplitter):
    def __init__(self, downloader: RemoteLogDownloader, parent=None):
        super().__init__(parent)
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

        self.sidebar_browse = QWidgetList(self)
        self.sidebar_browse.set_loading(True)
        self.sidebar_layout.addWidget(self.sidebar_browse)

    def populate(self):
        self.populate_thread = QThread()
        self.populate_worker = PopulateWorker(self.downloader)
        self.populate_worker.moveToThread(self.populate_thread)

        # Connect worker's finished/updates to UI methods
        self.populate_worker.finished.connect(self.set_items)
        self.populate_worker.finished.connect(
            lambda: self.sidebar_browse.set_loading(False)
        )
        self.populate_worker.progress.connect(self.sidebar_browse.set_progress)

        # Trigger run() via signal (runs in thread)
        self.populate_thread.started.connect(self.populate_worker.start.emit)

        # Clean up
        self.populate_worker.finished.connect(self.populate_thread.quit)
        self.populate_thread.finished.connect(self.populate_thread.deleteLater)

        self.populate_thread.start()

    def set_items(self, items: list):
        self.sidebar_browse.set_loading(False)
        print(items)

    def reload(self):
        self.sidebar_browse.clear_widgets()
        self.sidebar_browse.set_loading(True)
        self.populate()