# src/kevinbotlib/fileserver.py
import logging
import os
import threading
import traceback
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import override
import importlib.resources as resources

import jinja2
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

from kevinbotlib import __about__
from kevinbotlib.logger import Logger


def get_file_type(path):
    """Determine the file type for icon display."""
    if os.path.isdir(path):
        return "folder"

    # Get the file extension
    ext = os.path.splitext(path)[1].lower()

    # Define file type mappings
    type_mappings = {
        # Images
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
        ".txt": "text",
        ".md": "text",
        ".csv": "text",
        ".pdf": "pdf",
        ".zip": "archive",
        ".tar": "archive",
        ".gz": "archive",
        ".rar": "archive",
        ".log": "log",
    }

    return type_mappings.get(ext, "file")


class FileserverHTTPHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler with branded interface."""

    def __init__(self, *args, directory=None, **kwargs):
        # Set up template environment
        self.template_env = jinja2.Environment(
            loader=jinja2.PackageLoader("kevinbotlib.fileserver", "templates"),
            autoescape=True
        )
        self.static_dir = resources.files("kevinbotlib.fileserver.static")
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, fmt, *args):
        """Override to use project's logging system."""
        from kevinbotlib.logger import Logger

        logger = Logger()
        logger.info(f"HTTP: {fmt%args}")

    def list_directory(self, path):
        list_entries = os.listdir(path)
        list_entries.sort(key=lambda x: x.lower())

        # Create file entries with proper links
        entries = []
        for name in list_entries:
            fullname = os.path.join(path, name)
            displayname = name
            # Append / for directories
            if os.path.isdir(fullname):
                displayname = name + "/"
            # Convert to URL format
            urlname = urllib.parse.quote(name)
            filetype = get_file_type(fullname)
            entries.append((urlname, displayname, filetype))

        # Render template
        template = self.template_env.get_template("directory_listing.html")
        html_content = template.render(
            entries=entries, path=self.path, host=self.headers.get("Host", ""), version=__about__.__version__
        )

        encoded = html_content.encode("utf-8", "replace")
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()

        import io

        final_html = io.BytesIO(encoded)
        final_html.seek(0)

        return final_html
    
    @override
    def do_GET(self):
        """Handle GET requests, including serving static files."""
        # Check if this is a static file request
        if self.path.startswith("/static/"):
            resource_path = self.path.replace("/static/", "")
            
            # Attempt to find the resource in the package
            try:
                with resources.open_binary("kevinbotlib.fileserver.static", resource_path) as file:
                    # Determine content type
                    content_type = self.guess_type(resource_path)[0]

                    self.send_response(200)
                    self.send_header("Content-type", content_type)

                    # Send file length and other headers
                    file.seek(0, os.SEEK_END)
                    self.send_header("Content-Length", str(file.tell()))
                    self.end_headers()

                    # Reset the file pointer and send the file content
                    file.seek(0)
                    self.copyfile(file, self.wfile)

                    return
            except FileNotFoundError:
                pass

        return super().do_GET()


# Rest of the FileServer class remains the same...
class FileServer:
    """Combined FTP and HTTP file server for KevinBot."""

    def __init__(self, username: str, password: str, directory=".", ftp_port=2121, http_port=8000, host="127.0.0.1"):
        self.directory = os.path.abspath(directory)
        self.ftp_port = ftp_port
        self.http_port = http_port
        self.host = host
        self.username = username
        self.password = password
        self.ftp_thread = None
        self.http_thread = None

        self.logger = Logger()

    def start_ftp_server(self):
        """Start the FTP server in a separate thread."""

        ftp_logger = logging.getLogger("pyftpdlib")
        ftp_logger.addHandler(logging.StreamHandler())
        ftp_logger.setLevel(self.logger.level.value.no)

        def logging_redirect(record):
            log_level = next(key for key, val in logging.getLevelNamesMapping().items() if val == record.levelno)
            logger_opt = self.logger.loguru_logger.opt(depth=6, exception=record.exc_info)
            logger_opt.log(log_level, record.getMessage())

            return False

        ftp_logger.addFilter(logging_redirect)

        authorizer = DummyAuthorizer()
        authorizer.add_user(self.username, self.password, self.directory, perm="elradfmwMT")
        authorizer.add_anonymous(self.directory, perm="elr")

        handler = FTPHandler
        handler.authorizer = authorizer
        handler.banner = "Welcome to KevinbotLib FTP Server"

        self.ftpserver = FTPServer((self.host, self.ftp_port), handler)

        self.logger.info(f"FTP server starting on {self.host}:{self.ftp_port}")
        self.logger.info(f"Serving directory: {self.directory}")

        self.ftpserver.serve_forever()

    def start_http_server(self):
        """Start the HTTP server."""
        os.chdir(self.directory)

        def handler(*args):
            return FileserverHTTPHandler(*args, directory=self.directory)

        self.httpserver = HTTPServer((self.host, self.http_port), handler)

        self.logger.info(f"HTTP server starting on {self.host}:{self.http_port}")
        self.logger.info(f"Serving directory: {self.directory}")

        self.httpserver.serve_forever()

    def start(self):
        """Start both FTP and HTTP servers."""
        if not os.path.exists(self.directory):
            msg = f"Directory does not exist: {self.directory}"
            raise ValueError(msg)

        # Start FTP server in a thread
        self.ftp_thread = threading.Thread(target=self.start_ftp_server)
        self.ftp_thread.daemon = True
        self.ftp_thread.start()

        # Start HTTP server in a thread
        self.http_thread = threading.Thread(target=self.start_http_server)
        self.http_thread.daemon = True
        self.http_thread.start()

    def stop(self):
        """Stop the servers"""
        self.ftpserver.close()
        self.httpserver.shutdown()
