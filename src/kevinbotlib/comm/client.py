import json
import threading
import time
from collections.abc import Callable
from json import JSONDecodeError
from typing import ClassVar, TypeVar

import line_profiler
from orjson import orjson

from kevinbotlib.comm.abstract import AbstractPubSubNetworkClient, AbstractSetGetNetworkClient
from kevinbotlib.comm.core.client import NetworkClientCore
from kevinbotlib.comm.path import CommPath
from kevinbotlib.comm.sendables import (
    DEFAULT_SENDABLES,
    BaseSendable,
    SendableGenerator,
)
from kevinbotlib.exceptions import HandshakeTimeoutException
from kevinbotlib.logger import Logger as _Logger

T = TypeVar("T", bound=BaseSendable)


class NetworkClient(AbstractSetGetNetworkClient, AbstractPubSubNetworkClient):
    SENDABLE_TYPES: ClassVar[dict[str, type[BaseSendable]]] = DEFAULT_SENDABLES

    class _ConnectionLivelinessController:
        def __init__(self, *, dead: bool = False, on_disconnect: Callable[[], None] | None = None):
            self._dead = dead
            self._on_disconnect = on_disconnect

        @property
        def dead(self):
            return self._dead

        @dead.setter
        def dead(self, value):
            self._dead = value
            if value and self._on_disconnect:
                self._on_disconnect()

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8888,
        timeout: float = 2,
        on_connect: Callable[[], None] | None = None,
        on_disconnect: Callable[[], None] | None = None,
    ):
        self.core: NetworkClientCore | None = None
        self._host = host
        self._port = port
        self._timeout = timeout
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.running = False
        self.sub_thread: threading.Thread | None = None
        self.hooks: list[tuple[str, type[BaseSendable], Callable[[str, BaseSendable | None], None]]] = []
        self.sub_callbacks: dict[str, tuple[type[BaseSendable], Callable[[str, BaseSendable], None]]] = {}
        self._dead = self._ConnectionLivelinessController(dead=False, on_disconnect=self.on_disconnect)

    def register_type(self, data_type: type[BaseSendable]) -> None:
        """
        Register a custom sendable type.

        Args:
            data_type: Sendable type to register.
        """

        self.SENDABLE_TYPES[data_type.model_fields["data_id"].default] = data_type
        _Logger().trace(
            f"Registered data type of id {data_type.model_fields['data_id'].default} as {data_type.__name__}"
        )

    def add_hook(self, key: CommPath | str, data_type: type[T], callback: Callable[[str, T | None], None]) -> None:
        """
        Add a callback to be triggered when sendable of data_type is set for a key.

        Args:
            key: Key to listen to.
            data_type: Sendable type to listen for.
            callback: Callback to trigger.
        """

        self.hooks.append((str(key), data_type, callback))  # type: ignore

    def connect(self) -> None:
        """
        Attempt to connect to the server.
        """

        self.core = NetworkClientCore(
            host=self._host,
            port=self._port,
            timeout=self._timeout,
        )
        self._start_hooks()
        self.core.connect()

        for sub in self.sub_callbacks:
            self.core.subscribe(sub, self.sub_callbacks[sub][1])

        if self.on_connect:
            self.on_connect()

    def wait_until_connected(self, timeout: float = 5.0) -> None:
        """
        Wait until the connection is established.

        Args:
            timeout: Timeout in seconds. Defaults to 5.0 seconds.
        """

        start_time = time.time()
        while not self.core or not self.core.ping():
            if time.time() > start_time + timeout:
                self._dead.dead = True
                msg = "The connection timed out"
                raise HandshakeTimeoutException(msg)
            time.sleep(0.02)

    def reset_connection(self) -> None:
        """
        Attempt to reset the connection.
        """
        self.core.close()
        self.core = None
        self.connect()

    def close(self) -> None:
        """
        Close the socker connection.
        """
        self.core.close()
        self.core = None

    def is_connected(self) -> bool:
        """
        Check it the server is connected

        Returns:
            Connected?
        """
        return self.core and not self._dead.dead

    def get_latency(self) -> float | None:
        """
        Attempt to ping/pong the server and return the round-trip latency.

        Returns:
            Round-trip latency in seconds or None.
        """
        if not self.core:
            return None
        return self.core.get_latency()

    def _apply(
        self,
        key: CommPath | str,
        sendable: BaseSendable | SendableGenerator,
        *,
        pub_mode: bool = False,
    ):
        if not self.running or not self.core:
            _Logger().error(f"Cannot publish/set to {key}: client is not started")
            return

        if isinstance(sendable, SendableGenerator):
            sendable = sendable.generate_sendable()

        data = sendable.get_dict()
        try:
            if pub_mode:
                if sendable.timeout:
                    _Logger().warning("Publishing a Sendable with a timeout. Pub/Sub does not support this.")
                self.core.pub(str(key), orjson.dumps(data))
            elif sendable.timeout:
                self.core.set(str(key), orjson.dumps(data), px=int(sendable.timeout * 1000))
            else:
                self.core.set(str(key), orjson.dumps(data))
            self._dead.dead = False
        except ConnectionError as e:
            _Logger().error(f"Cannot publish/set to {key}: {e}")
            if not self.core:
                self._dead.dead = True
            else:
                _Logger().warning("Connection changed while getting ping to server. Connection may not be dead.")

    def set(self, key: CommPath | str, sendable: BaseSendable | SendableGenerator) -> None:
        """
        Set sendable in the server.

        Args:
            key: Key to set
            sendable: Sendable to set
        """

        self._apply(key, sendable, pub_mode=False)

    @line_profiler.profile
    def get(self, key: CommPath | str, data_type: type[T]) -> T | None:
        """
        Retrieve and deserialize sendable by key.

        Args:
            key: Key to retrieve.
            data_type: Sendable type to deserialize to.

        Returns:
            Sendable or None if not found.
        """

        if not self.core:
            _Logger().error("Cannot get data: client is not started")
            return None
        try:
            raw = self.core.get(str(key))
            self._dead.dead = False
        except (ConnectionError, TimeoutError) as e:
            _Logger().error(f"Cannot get {key}: {e}")
            self._dead.dead = True
            return None
        if raw is None:
            return None
        try:
            data = orjson.loads(raw)
            if data_type:
                return data_type(**data)
        except (orjson.JSONDecodeError, JSONDecodeError, KeyError):
            pass
        return None

    def get_raw(self, key: CommPath | str) -> dict | None:
        """
        Retrieve the raw JSON for a key, ignoring the sendable deserialization.

        Args:
            key: Key to retrieve.

        Returns:
            Raw JSON value or None if not found.
        """

        if not self.core:
            _Logger().error("Cannot get raw: client is not started")
            return None
        try:
            raw = self.core.get(str(key))
            self._dead.dead = False
            return orjson.loads(raw) if raw else None
        except (ConnectionError, TimeoutError) as e:
            _Logger().error(f"Cannot get raw {key}: {e}")
            self._dead.dead = True
            return None

    def get_all_raw(self) -> dict[str, dict] | None:
        """
        Retrieve all raw JSON values as a dictionary of a key to raw value. May have slow performance.

        Returns:
            Dictionary of a key to raw value or None if not found.
        """
        if not self.core:
            _Logger().error("Cannot get all raw: client is not started")
            return None
        try:
            keys = self.core.get_all_keys()
            if not keys:
                self._dead.dead = False
                return {}

            values = [self.core.get(key) for key in keys]
            self._dead.dead = False

            # Construct result dictionary, decoding JSON values
            result = {}
            for key, value in zip(keys, values, strict=False):
                if value:
                    result[key] = orjson.loads(value)
        except (ConnectionError, TimeoutError) as e:
            _Logger().error(f"Cannot get all raw: {e}")
            self._dead.dead = True
            return None
        else:
            return result

    def get_keys(self) -> list[str]:
        """
        Get all keys in the server.

        Returns:
            List of keys
        """
        return self.core.get_all_keys() if self.core else []

    def publish(self, key: CommPath | str, sendable: BaseSendable | SendableGenerator) -> None:
        """
        Publish sendable in the Pub/Sub server.

        Args:
            key: Key to publish to
            sendable: Sendable to publish
        """

        self._apply(key, sendable, pub_mode=True)

    def subscribe(self, key: CommPath | str, data_type: type[T], callback: Callable[[str, T], None]) -> None:
        """
        Subscribe to a Pub/Sub key.

        Args:
            key: Key to subscribe to.
            data_type: Sendable type to deserialize to.
            callback: Callback when data is received.
        """

        if isinstance(key, CommPath):
            key = str(key)
        key_str = str(key)
        self.sub_callbacks[key_str] = (data_type, callback)  # type: ignore
        if self.core:
            try:

                def on_msg(channel, data):
                    callback(channel, data_type(**orjson.loads(data)))

                self.core.subscribe(key_str, on_msg)
            except (ConnectionError, TimeoutError) as e:
                _Logger().error(f"Cannot subscribe to {key_str}: {e}")
        else:
            _Logger().error(f"Can't subscribe to {key}, Pub/Sub is not running")

    def delete(self, key: CommPath | str) -> None:
        """
        Delete a key from the server.

        Args:
            key: Key to delete.
        """

        if not self.core:
            _Logger().error("Cannot delete: client is not started")
            return
        try:
            self.core.delete(str(key))
            self._dead.dead = False
        except (ConnectionError, TimeoutError) as e:
            _Logger().error(f"Cannot delete {key}: {e}")
            self._dead.dead = True

    def wipeall(self) -> None:
        """
        Delete all keys from the server.

        Args:
            key: Key to delete.
        """

        if not self.core:
            _Logger().error("Cannot delete: client is not started")
            return
        try:
            self.core.clear()
            self._dead.dead = False
        except (ConnectionError, TimeoutError) as e:
            _Logger().error(f"Cannot wipe: {e}")
            self._dead.dead = True

    def _start_hooks(self) -> None:
        if not self.running:
            self.running = True
            self.sub_thread = threading.Thread(
                target=self._run_hooks, daemon=True, name="KevinbotLib.Networking.Client.Hooks"
            )
            self.sub_thread.start()

    def _run_hooks(self):
        """Run the pubsub listener in a separate thread."""
        previous_values = {}
        while True:
            # update previous values with hook keys
            try:
                if not self.running:
                    break
                if not self.core:
                    time.sleep(0.01)
                    continue
                for key, _, _ in self.hooks:
                    if key not in previous_values:
                        previous_values[key] = None
                    if not self.core:
                        continue
                    message = self.core.get(key)
                    if message != previous_values[key]:
                        # Call the hook
                        for ckey, data_type, callback in self.hooks:
                            try:
                                raw = self.core.get(ckey)
                                if raw:
                                    data = orjson.loads(raw)
                                    if data["did"] == data_type(**data).data_id:
                                        sendable = self.SENDABLE_TYPES[data["did"]](**data)
                                        callback(ckey, sendable)
                                else:
                                    callback(ckey, None)
                            except (orjson.JSONDecodeError, KeyError):
                                pass
                    previous_values[key] = message
                self._dead.dead = False
            except (ConnectionError, TimeoutError):
                self._dead.dead = True
            except (AttributeError, ValueError) as e:
                _Logger().error(f"Something went wrong while processing hooks: {e!r}")
            if not self.running:
                break
            time.sleep(0.01)

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @host.setter
    def host(self, value: str):
        self._host = value
        self.reset_connection()

    @port.setter
    def port(self, value: int):
        self._port = value
        self.reset_connection()

    @property
    def timeout(self) -> float:
        return self._timeout

    @timeout.setter
    def timeout(self, value: float) -> None:
        self._timeout = value
        if self.core:
            self.core.timeout = value
