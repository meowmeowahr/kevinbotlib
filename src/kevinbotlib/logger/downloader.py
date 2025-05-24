import paramiko
from typing import List
import os

from kevinbotlib.exceptions import SshNotConnectedException
from kevinbotlib.logger.parser import LogEntry, LogParser


class RemoteLogDownloader:
    default_missing_host_key_policy = paramiko.WarningPolicy()

    def __init__(self, log_dir: str = "~/.local/share/kevinbotlib/logging/"):
        self.ssh_connection = None
        self.sftp_client = None
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
            # Get the absolute path of the home directory
            home_dir = self.sftp_client.normalize(".")
            # Replace ~ with the actual home directory path
            relative_path = self._log_dir[1:].lstrip("/")
            self._resolved_log_dir = os.path.join(home_dir, relative_path)
        else:
            self._resolved_log_dir = self._log_dir

        return self._resolved_log_dir

    def connect_with_password(self, host: str, username: str, password: str, port: int = 22, missing_host_key_policy: paramiko.MissingHostKeyPolicy = default_missing_host_key_policy):
        self.ssh_connection = paramiko.SSHClient()
        self.ssh_connection.set_missing_host_key_policy(missing_host_key_policy)
        self.ssh_connection.connect(hostname=host, username=username, password=password, port=port)
        self.sftp_client = self.ssh_connection.open_sftp()
        self._resolved_log_dir = None

    def connect_with_key(self, host: str, key: paramiko.RSAKey, port: int = 22, missing_host_key_policy: paramiko.MissingHostKeyPolicy = default_missing_host_key_policy):
        self.ssh_connection = paramiko.SSHClient()
        self.ssh_connection.set_missing_host_key_policy(missing_host_key_policy)
        self.ssh_connection.connect(hostname=host, pkey=key, port=port)
        self.sftp_client = self.ssh_connection.open_sftp()
        self._resolved_log_dir = None

    def disconnect(self):
        if self.ssh_connection:
            self.ssh_connection.close()
            self.ssh_connection = None
        if self.sftp_client:
            self.sftp_client.close()
            self.sftp_client = None

    def get_logfiles(self) -> List[str]:
        if not self.ssh_connection or not self.sftp_client:
            msg = "SFTP is not connected"
            raise SshNotConnectedException(msg)

        resolved_path = self._resolve_log_dir()
        files =  self.sftp_client.listdir(resolved_path)
        for file in reversed(files):
            if not file.endswith(".log"):
                files.remove(file)
        return files

    def get_raw_log(self, logfile: str) -> str:
        if not self.ssh_connection or not self.sftp_client:
            msg = "SFTP is not connected"
            raise SshNotConnectedException(msg)

        resolved_path = self._resolve_log_dir()
        return self.sftp_client.open(os.path.join(resolved_path, logfile)).read().decode("utf-8")

    def get_log(self, logfile: str) -> list[LogEntry]:
        if not self.ssh_connection or not self.sftp_client:
            msg = "SFTP is not connected"
            raise SshNotConnectedException(msg)

        resolved_path = self._resolve_log_dir()
        raw = self.sftp_client.open(os.path.join(resolved_path, logfile)).read().decode("utf-8")
        return LogParser.parse(raw)