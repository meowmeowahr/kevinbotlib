import codecs
import random
import socket
import string
import time

import line_profiler
from line_profiler import profile

from kevinbotlib.comm.path import CommPath
from kevinbotlib.logger import Logger


class NetworkClientCore:
    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
        self.sock: socket.socket | None = None

    def connect(self):
        """Connects to the server."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self._host, self._port))
            Logger().info(f"Connected to {self._host}:{self._port}")
        except OSError as e:
            Logger().error(f"Could not connect to server: {e}")
            self.sock = None
            raise

    def close(self):
        """Closes the connection."""
        if self.sock:
            self.sock.close()
            self.sock = None
            Logger().info("Disconnected from server.")

    @profile
    def raw_send(self, message: str) -> str:
        """Sends a message and receives a response."""
        if not self.sock:
            msg = "Client not connected."
            raise RuntimeError(msg)

        try:
            full_message = codecs.encode((message + "\n"), "utf-8")
            self.sock.sendall(full_message)

            response_data = bytearray()
            while True:
                chunk = self.sock.recv(65536 * 2)  # Read in chunks
                response_data += chunk
                if b"\n" in chunk:  # Assume responses are line-terminated
                    break
            return response_data.decode().strip()
        except OSError as e:
            Logger().error(f"Socket error during communication: {e}")
            self.close()  # Attempt to clean up
            raise

    @profile
    def set(self, key: CommPath | str, value: str) -> bool:
        """Sets a key-value pair on the server."""
        response = self.raw_send(f"SET {key} {value}")
        return response == "OK"

    @profile
    def get(self, key: CommPath | str) -> str | None:
        """Gets a value for a given key from the server."""
        response = self.raw_send(f"GET {key}")
        if response.startswith("ERROR"):
            Logger().warning(f"GET operation for {key} failed: {response}")
            return None
        return None

    @profile
    def delete(self, key: CommPath | str) -> bool:
        """Deletes a key-value pair from the server."""
        response = self.raw_send(f"DEL {key}")
        return response == "OK"

    def is_connected(self) -> bool:
        return self.sock is not None and self.sock.fileno() != -1

    def is_ready(self) -> bool:
        return self.raw_send("RDY") == "OK"

    def reset_connection(self):
        self.close()
        self.connect()

    def get_latency(self) -> float | None:
        """
        Measure the round-trip latency to the server in milliseconds.

        Returns:
            Latency in milliseconds or None if not connected.
        """
        if not self.sock:
            return None
        start_time = time.perf_counter()
        if self.raw_send("PING") == "PONG":
            end_time = time.perf_counter()
            return (end_time - start_time) * 1000
        return None

    @property
    def host(self) -> str:
        return self._host

    @host.setter
    def host(self, value: str):
        self._host = value
        self.reset_connection()

    @property
    def port(self) -> int:
        return self._port

    @port.setter
    def port(self, value: int):
        self._port = value
        self.reset_connection()

    @property
    def timeout(self) -> float:
        return self.sock.timeout
