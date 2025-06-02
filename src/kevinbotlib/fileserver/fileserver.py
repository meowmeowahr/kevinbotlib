import contextlib
import os
import threading
import urllib.parse
from importlib import resources
from wsgiref.simple_server import make_server

import jinja2

from kevinbotlib import __about__
from kevinbotlib.logger import Level, Logger, StreamRedirector


def get_file_type(path: str) -> str:
    """
    Get the icon name from a file extension.

    Args:
        path: File path

    Returns: Icon name
    """

    if os.path.isdir(path):
        return "folder"
    ext = os.path.splitext(path)[1].lower()
    type_mappings = {
        ".jpg": "image",
        ".jpeg": "image",
        ".png": "image",
        ".gif": "image",
        ".svg": "image",
        ".py": "code",
        ".js": "code",
        ".html": "code",
        ".css": "code",
        ".cpp": "code",
        ".h": "code",
        ".pdf": "pdf",
        ".zip": "archive",
        ".tar": "archive",
        ".gz": "archive",
        ".rar": "archive",
        ".log": "log",
    }
    return type_mappings.get(ext, "file")


class FileserverHTTPHandler:
    """Custom WSGI handler for file serving."""

    def __init__(self, directory):
        self.directory = directory
        self.template_env = jinja2.Environment(
            loader=jinja2.PackageLoader("kevinbotlib.fileserver", "templates"),
            autoescape=True,
        )
        self.static_dir = resources.files("kevinbotlib.fileserver.static")
        self.logger = Logger()

    def list_directory(self, path):
        """Generate directory listing as HTML."""
        # Normalize path: ensure root is "/"
        path = "/" if not path or path == "" else "/" + path.lstrip("/")
        full_path = os.path.join(self.directory, path.lstrip("/"))
        if not os.path.exists(full_path):
            self.logger.warning(f"Directory not found: {full_path}")
            return None, 404

        self.logger.debug(f"Listing directory: {full_path}")
        list_entries = os.listdir(full_path)
        list_entries.sort(key=lambda x: x.lower())

        entries = []
        for name in list_entries:
            fullname = os.path.join(full_path, name)
            displayname = name + "/" if os.path.isdir(fullname) else name
            relative_path = os.path.relpath(fullname, self.directory).replace("\\", "/")
            urlname = urllib.parse.quote(relative_path)
            filetype = get_file_type(fullname)
            entries.append((urlname, displayname, filetype))

        template = self.template_env.get_template("directory_listing.html")
        html_content = template.render(
            entries=entries,
            path=path,
            host="",
            version=__about__.__version__,
        )
        self.logger.debug(f"Rendered directory listing for {path}")
        return html_content.encode("utf-8"), 200

    def serve_static(self, resource_path: str):
        """Serve static files from the package."""
        try:
            with resources.open_binary(
                f"kevinbotlib.fileserver.static.{'.'.join(resource_path.split('/')[:-1])}", resource_path.split("/")[-1]
            ) as file:
                content_type = self.guess_type(resource_path)
                file_content = file.read()
                return file_content, 200, content_type
        except FileNotFoundError:
            return b"File not found", 404, "text/plain"

    def guess_type(self, path):
        """Simplified content type guessing."""
        ext = os.path.splitext(path)[1].lower()
        mime_types = {
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".pdf": "application/pdf",
            ".json": "application/json",
            ".log": "text/plain",
        }
        return mime_types.get(ext, "application/octet-stream")

    def __call__(self, environ, start_response):
        """WSGI callable."""
        path = environ.get("PATH_INFO", "/").lstrip("/")
        self.logger.trace(f"HTTP: {environ['REQUEST_METHOD']} {path}")

        if path.startswith("static/"):
            resource_path = path.replace("static/", "")
            body, status, content_type = self.serve_static(resource_path)
            status_line = f"{status} {'OK' if status == 200 else 'Not Found'}"  # noqa: PLR2004
            headers = [("Content-Type", content_type), ("Content-Length", str(len(body)))]
            start_response(status_line, headers)
            return [body]

        # Serve file or directory
        full_path = os.path.join(self.directory, path)
        if os.path.isdir(full_path):
            body, status = self.list_directory(path)
            if body is None:
                start_response("404 Not Found", [("Content-Type", "text/plain")])
                return [b"Directory not found"]
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))])
            return [body]
        if os.path.isfile(full_path):
            with open(full_path, "rb") as f:
                body = f.read()
            content_type = self.guess_type(full_path)
            start_response("200 OK", [("Content-Type", content_type), ("Content-Length", str(len(body)))])
            return [body]
        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"File not found"]


class FileServer:
    """Simple HTTP file server for KevinbotLib"""

    def __init__(
        self,
        directory: str = ".",
        http_port: int = 8000,
        host: str = "172.0.0.1",
    ):
        """
        Initialize the file server.

        Args:
            directory: Directory to serve. Defaults to "."
            http_port: Port to serve on. Defaults to 8000.
            host: Host to serve on. Defaults to "127.0.0.1".
        """

        self.http_thread: threading.Thread | None = None
        self.directory = os.path.abspath(directory)
        self.http_port = http_port
        self.host = host
        self.http_server = None
        self.logger = Logger()

    def http_server_loop(self) -> None:
        """
        Start the WSGI file server
        """

        app = FileserverHTTPHandler(self.directory)
        self.http_server = make_server(self.host, self.http_port, app)
        self.logger.info(f"HTTP server starting on {self.host}:{self.http_port}")
        self.logger.info(f"Serving directory: {self.directory}")
        with contextlib.redirect_stderr(StreamRedirector(self.logger, Level.DEBUG)):
            self.http_server.serve_forever()

    def start(self, name: str = "KevinbotLib.FileServer.Serve") -> None:
        """
        Start the HTTP server.

        Args:
            name: Name of the server thread. Defaults to "KevinbotLib.FileServer.Serve".
        """

        if not os.path.exists(self.directory):
            msg = f"Directory does not exist: {self.directory}"
            raise ValueError(msg)

        self.http_thread = threading.Thread(target=self.http_server_loop, name=name)
        self.http_thread.daemon = True
        self.http_thread.start()

    def stop(self) -> None:
        """Shutdown the HTTP server."""

        if self.http_server:
            self.http_server.shutdown()
