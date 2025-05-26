import datetime
import os
import tempfile
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

import paramiko

from kevinbotlib.exceptions import SshNotConnectedException
from kevinbotlib.logger import Logger
from kevinbotlib.logger.parser import Log, LogParser

if TYPE_CHECKING:
    from paramiko.sftp_client import SFTPClient


class RemoteLogDownloader:
    """Tool for downloading logs from a remote host using SFTP."""

    default_missing_host_key_policy = paramiko.WarningPolicy()

    def __init__(self, log_dir: str = "~/.local/share/kevinbotlib/logging/"):
        self.ssh_connection = None
        self.sftp_client: SFTPClient | None = None
        self._log_dir = log_dir
        self._resolved_log_dir = None

    @property
    def log_dir(self) -> str:
        return self._log_dir

    @log_dir.setter
    def log_dir(self, value: str):
        self._log_dir = value
        self._resolved_log_dir = None  # Reset the resolved path when log_dir changes

    def _resolve_log_dir(self) -> str:
        """Resolve the log_dir path, expanding ~ to the user's home directory."""
        if self._resolved_log_dir:
            return self._resolved_log_dir
        if not self.sftp_client:
            msg = "SFTP is not connected"
            raise SshNotConnectedException(msg)

        # If the path starts with ~, resolve the home directory
        if self._log_dir.startswith("~"):
            home_dir = self.sftp_client.normalize(".")
            relative_path = self._log_dir[1:].lstrip("/")
            self._resolved_log_dir = os.path.join(home_dir, relative_path)
        else:
            self._resolved_log_dir = self._log_dir

        # Verify the directory exists
        self.sftp_client.stat(self._resolved_log_dir)
        return self._resolved_log_dir

    def connect_with_password(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 22,
        missing_host_key_policy: paramiko.MissingHostKeyPolicy = default_missing_host_key_policy,
    ):
        """Connect to a remote host using a password."""
        Logger().debug("Attempting Password connection")

        self.ssh_connection = paramiko.SSHClient()
        self.ssh_connection.set_missing_host_key_policy(missing_host_key_policy)
        self.ssh_connection.connect(hostname=host, username=username, password=password, port=port, timeout=10)
        self.sftp_client = self.ssh_connection.open_sftp()
        self._resolved_log_dir = None

    def connect_with_key(
        self,
        host: str,
        username: str,
        key: paramiko.RSAKey,
        port: int = 22,
        missing_host_key_policy: paramiko.MissingHostKeyPolicy = default_missing_host_key_policy,
    ):
        """Connect to a remote host using a Paramiko RSA key."""
        Logger().debug("Attempting RSAKey connection")

        self.ssh_connection = paramiko.SSHClient()
        self.ssh_connection.set_missing_host_key_policy(missing_host_key_policy)
        self.ssh_connection.connect(hostname=host, username=username, pkey=key, port=port, timeout=10)
        self.sftp_client = self.ssh_connection.open_sftp()
        self._resolved_log_dir = None

    def disconnect(self):
        if self.ssh_connection:
            self.ssh_connection.close()
        self.ssh_connection = None
        if self.sftp_client:
            self.sftp_client.close()
        self.sftp_client = None

    def get_logfiles(self) -> list[str]:
        if not self.ssh_connection or not self.sftp_client:
            msg = "SFTP is not connected"
            raise SshNotConnectedException(msg)

        resolved_path = self._resolve_log_dir()
        files = self.sftp_client.listdir(resolved_path)
        return [file for file in files if file.endswith(".log")]

    @contextmanager
    def _download_with_progress(
        self, remote_path: str, progress_callback: Callable[[float], None] | None = None
    ) -> Generator[str, Any, None]:
        """Download a remote file to a temporary local file with optional progress callback."""
        if not self.ssh_connection or not self.sftp_client:
            msg = "SFTP is not connected"
            raise SshNotConnectedException(msg)

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            try:

                def callback(transferred: int, total: int):
                    if progress_callback and total > 0:
                        progress_percent = (transferred / total) * 100.0
                        progress_callback(progress_percent)

                self.sftp_client.get(remote_path, temp_file.name, callback=callback if progress_callback else None)

                with open(temp_file.name, encoding="utf-8") as f:
                    yield f.read()
            finally:
                try:
                    os.unlink(temp_file.name)
                except OSError as e:
                    Logger().warning(f"Failed to delete temporary file {temp_file.name}: {e!s}")

    def get_raw_log(self, logfile: str, progress_callback: Callable[[float], None] | None = None) -> str:
        resolved_path = self._resolve_log_dir()
        remote_path = os.path.join(resolved_path, logfile)
        with self._download_with_progress(remote_path, progress_callback) as content:
            return content

    def delete_log(self, logfile: str):
        resolved_path = self._resolve_log_dir()
        remote_path = os.path.join(resolved_path, logfile)
        self.sftp_client.remove(remote_path)

    def get_log(self, logfile: str, progress_callback: Callable[[float], None] | None = None) -> Log:
        resolved_path = self._resolve_log_dir()
        remote_path = os.path.join(resolved_path, logfile)
        with self._download_with_progress(remote_path, progress_callback) as raw:
            return LogParser.parse(raw)

    def get_file_modification_time(self, logfile: str) -> datetime.datetime:
        if not self.ssh_connection or not self.sftp_client:
            msg = "SFTP is not connected"
            raise SshNotConnectedException(msg)

        resolved_path = self._resolve_log_dir()
        return datetime.datetime.fromtimestamp(
            self.sftp_client.stat(os.path.join(resolved_path, logfile)).st_mtime, tz=datetime.timezone.utc
        )

    def get_file_size(self, logfile: str) -> int:
        if not self.ssh_connection or not self.sftp_client:
            msg = "SFTP is not connected"
            raise SshNotConnectedException(msg)

        resolved_path = self._resolve_log_dir()
        return self.sftp_client.stat(os.path.join(resolved_path, logfile)).st_size
