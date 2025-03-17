import contextlib
import logging
import os
import threading
import urllib.parse
from importlib import resources

import jinja2
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from wsgiref.simple_server import make_server

from kevinbotlib import __about__
from kevinbotlib.logger import Level, Logger, StreamRedirector

# Your existing get_file_type function remains unchanged
def get_file_type(path):
    """Determine the file type for icon display."""
    if os.path.isdir(path):
        return "folder"
    ext = os.path.splitext(path)[1].lower()
    type_mappings = {
        ".jpg": "image", ".jpeg": "image", ".png": "image", ".gif": "image", ".svg": "image",
        ".py": "code", ".js": "code", ".html": "code", ".css": "code", ".cpp": "code", ".h": "code",
        ".pdf": "pdf",
        ".zip": "archive", ".tar": "archive", ".gz": "archive", ".rar": "archive", ".log": "log",
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

    def serve_static(self, resource_path):
        """Serve static files from the package."""
        try:
            with resources.open_binary("kevinbotlib.fileserver.static", resource_path) as file:
                content_type = self.guess_type(resource_path)
                file_content = file.read()
                return file_content, 200, content_type
        except FileNotFoundError:
            return b"File not found", 404, "text/plain"

    def guess_type(self, path):
        """Simplified content type guessing."""
        ext = os.path.splitext(path)[1].lower()
        mime_types = {
            ".html": "text/html", ".css": "text/css", ".js": "application/javascript",
            ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
            ".svg": "image/svg+xml", ".pdf": "application/pdf", ".json": "application/json", ".log": "text/plain",
        }
        return mime_types.get(ext, "application/octet-stream")

    def __call__(self, environ, start_response):
        """WSGI callable."""
        path = environ.get("PATH_INFO", "/").lstrip("/")
        self.logger.trace(f"HTTP: {environ['REQUEST_METHOD']} {path}")

        if path.startswith("static/"):
            resource_path = path.replace("static/", "")
            body, status, content_type = self.serve_static(resource_path)
            status_line = f"{status} {'OK' if status == 200 else 'Not Found'}"
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
        elif os.path.isfile(full_path):
            with open(full_path, "rb") as f:
                body = f.read()
            content_type = self.guess_type(full_path)
            start_response("200 OK", [("Content-Type", content_type), ("Content-Length", str(len(body)))])
            return [body]
        else:
            start_response("404 Not Found", [("Content-Type", "text/plain")])
            return [b"File not found"]

class FileServer:
    """Combined FTP and HTTP file server for KevinBot."""
    def __init__(self, directory=".", ftp_port=2121, http_port=8000, host="127.0.0.1", *, enable_ftp_server: bool = False):
        self.directory = os.path.abspath(directory)
        self.ftp_port = ftp_port
        self._ftp_enabled = enable_ftp_server
        self.http_port = http_port
        self.host = host
        self.ftp_thread = None
        self.http_server = None
        self.logger = Logger()

    def start_ftp_server(self):
        """Start the FTP server in a separate thread."""
        ftp_logger = logging.getLogger("pyftpdlib")
        ftp_logger.addHandler(logging.StreamHandler())
        ftp_logger.setLevel(Level.DEBUG.value.no)

        def logging_redirect(record):
            log_level = next(key for key, val in logging.getLevelNamesMapping().items() if val == record.levelno)
            logger_opt = self.logger.loguru_logger.opt(depth=6, exception=record.exc_info)
            logger_opt.log(log_level, record.getMessage())
            return False

        ftp_logger.addFilter(logging_redirect)

        authorizer = DummyAuthorizer()
        authorizer.add_anonymous(self.directory, perm="elradfmwMT")
        handler = FTPHandler
        handler.authorizer = authorizer
        handler.banner = "Welcome to KevinbotLib FTP Server"
        self.ftpserver = FTPServer((self.host, self.ftp_port), handler)

        self.logger.info(f"FTP server starting on {self.host}:{self.ftp_port}")
        self.ftpserver.serve_forever()

    def start_http_server(self):
        """Start the WSGI server."""
        app = FileserverHTTPHandler(self.directory)
        self.http_server = make_server(self.host, self.http_port, app)
        self.logger.info(f"HTTP server starting on {self.host}:{self.http_port}")
        self.logger.info(f"Serving directory: {self.directory}")
        with contextlib.redirect_stderr(StreamRedirector(self.logger, Level.DEBUG)):
            self.http_server.serve_forever()

    def start(self, name: str = "KevinbotLib.FileServer.Serve"):
        """Start both FTP and HTTP servers."""
        if not os.path.exists(self.directory):
            raise ValueError(f"Directory does not exist: {self.directory}")

        if self._ftp_enabled:
            self.ftp_thread = threading.Thread(target=self.start_ftp_server)
            self.ftp_thread.daemon = True
            self.ftp_thread.start()
            self.logger.security(
                "FTP server enabled. This is a security vulnerability and will be removed in a future version."
            )

        self.http_thread = threading.Thread(target=self.start_http_server, name=name)
        self.http_thread.daemon = True
        self.http_thread.start()

    def stop(self):
        """Stop the servers."""
        if self._ftp_enabled and hasattr(self, "ftpserver"):
            self.ftpserver.close()
        if self.http_server:
            self.http_server.shutdown()
