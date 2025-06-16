import socket
import threading
import time

import line_profiler
from kevinbotlib.logger import Logger


class NetworkClientCore:
    def __init__(self, host: str, port: int, timeout: float = 5):
        self._host = host
        self._port = port
        self._timeout = timeout
        self.setget_sock: socket.socket | None = None
        self.pubsub_sock: socket.socket | None = None
        self.sub_sockets = {}  # pattern -> socket
        self.sub_threads = {}
        self.sub_stop_flags = {}

    def _connect_role(self, role: str) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self._host, self._port))
        sock.sendall((f"ROLE {role}\n").encode())
        sock.settimeout(self._timeout)
        return sock

    def connect(self):
        self.setget_sock = self._connect_role("SETGET")
        Logger().info("Connected SETGET socket")

        self.pubsub_sock = self._connect_role("PUBSUB")
        Logger().info("Connected main PUBSUB socket")

    @line_profiler.profile
    def raw_send(self, message: str) -> str:
        if not self.setget_sock:
            raise RuntimeError("Not connected.")
        self.setget_sock.sendall((message + "\n").encode())
        response = b""
        while True:
            chunk = self.setget_sock.recv(4096)
            response += chunk
            if b"\n" in chunk:
                break
        return response.decode().strip()

    def set(self, key: str, value: str, px: int | None = None) -> bool:
        return (self.raw_send(f"SET {key} {value}") if not px else self.raw_send(f"SETX {key} {px} {value}")) == "OK"

    @line_profiler.profile
    def get(self, key: str) -> str | None:
        response = self.raw_send(f"GET {key}")
        return None if response.startswith("ERROR") else response

    def delete(self, key: str) -> bool:
        return self.raw_send(f"DEL {key}") == "OK"

    def clear(self) -> bool:
        return self.raw_send("CLR") == "OK"

    def pub(self, key: str, value: str) -> bool:
        sock = self._connect_role("PUBSUB")
        sock.sendall(f"PUB {key} {value}\n".encode())
        response = sock.recv(4096).decode().strip()
        sock.close()
        return response == "OK"

    def subscribe(self, pattern: str, on_message=None):
        if pattern in self.sub_threads:
            Logger().warning(f"Already subscribed to {pattern}")
            return

        sub_sock = self._connect_role("PUBSUB")
        sub_sock.sendall(f"SUB {pattern}\n".encode())

        stop_flag = threading.Event()

        def listen():
            try:
                while not stop_flag.is_set():
                    data = sub_sock.recv(4096)
                    if not data:
                        break
                    for line in data.decode().strip().split("\n"):
                        if line.startswith("PUB "):
                            _, key, value = line.split(" ", 2)
                            if on_message:
                                on_message(key, value)
            except Exception:
                pass
            finally:
                sub_sock.close()
                Logger().info(f"Subscription to {pattern} closed.")

        thread = threading.Thread(target=listen, daemon=True)
        self.sub_sockets[pattern] = sub_sock
        self.sub_threads[pattern] = thread
        self.sub_stop_flags[pattern] = stop_flag
        thread.start()

    def unsubscribe(self, pattern: str):
        if pattern not in self.sub_threads:
            return
        self.sub_stop_flags[pattern].set()
        sock = self.sub_sockets.pop(pattern)
        sock.sendall(f"UNSUB {pattern}\n".encode())
        sock.close()
        thread = self.sub_threads.pop(pattern)
        thread.join(timeout=2)

    def ping(self) -> bool:
        return self.raw_send("PING") == "PONG"

    def close(self):
        for pattern in list(self.sub_threads.keys()):
            self.unsubscribe(pattern)
        if self.setget_sock:
            self.setget_sock.close()
            self.setget_sock = None
            Logger().info("Disconnected SETGET socket")
