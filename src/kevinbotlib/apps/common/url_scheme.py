from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtWebEngineCore import (
    QWebEngineUrlRequestJob,
    QWebEngineUrlScheme,
    QWebEngineUrlSchemeHandler,
)

from kevinbotlib.logger import Logger

URL_SCHEME = "logdata"


class LogUrlSchemeHandler(QWebEngineUrlSchemeHandler):
    """URL scheme handler to serve large HTML content for logs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.html_data = ""

    def store_html(self, data: str):
        """Store HTML content for serving."""
        self.html_data = data

    def requestStarted(self, job: QWebEngineUrlRequestJob):  # noqa: N802
        """Handle requests for our custom scheme."""
        path = job.requestUrl().path()

        if self.html_data is not None:
            data = str(self.html_data).encode("utf-8")
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
        | QWebEngineUrlScheme.Flag.LocalScheme  # type: ignore
        | QWebEngineUrlScheme.Flag.LocalAccessAllowed
    )
    QWebEngineUrlScheme.registerScheme(scheme)
