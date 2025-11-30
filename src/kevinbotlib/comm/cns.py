import json
import socket
import threading
import time
import uuid
from collections.abc import Callable
from typing import ClassVar, TypeVar, final

import orjson
import websockets
from kevinbotlib_cns.client import CNSClient
from kevinbotlib_cns.types import JSONType
from pydantic import ValidationError

import kevinbotlib.exceptions
from kevinbotlib.comm.abstract import (
    AbstractPubSubNetworkClient,
    AbstractSetGetNetworkClient,
)
from kevinbotlib.comm.path import CommPath
from kevinbotlib.comm.request import GetRequest, SetRequest
from kevinbotlib.comm.sendables import (
    DEFAULT_SENDABLES,
    BaseSendable,
    SendableGenerator,
)
from kevinbotlib.logger import Logger as _Logger

__all__ = ["CNSCommClient"]

T = TypeVar("T", bound=BaseSendable)


class CNSCommClient(AbstractSetGetNetworkClient, AbstractPubSubNetworkClient):
    """CNS Communication Client - a drop-in replacement for RedisCommClient using kevinbotlib_cns.client."""
    
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
        port: int = 4800,
        timeout: float = 5,
        on_connect: Callable[[], None] | None = None,
        on_disconnect: Callable[[], None] | None = None,
    ) -> None:
        """
        Initialize a CNS (Communication & Networking Service) Client.

        Args:
            host: Host of the CNS server.
            port: Port of the CNS server.
            timeout: Socket timeout in seconds (NOTE: CNS doesn't support timeouts natively).
            on_connect: Connection callback.
            on_disconnect: Disconnection callback.
        """

        self.client: CNSClient | None = None
        self._host = host
        self._port = port
        self._timeout = timeout  # TODO: CNS doesn't support timeouts
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.hooks: list[tuple[str, type[BaseSendable], Callable[[str, BaseSendable | None], None]]] = []
        self._flag_robot: str | None = None # to be set by BaseRobot
        self._client_id: str | None = None

        self._lock = threading.Lock()
        self._dead: CNSCommClient._ConnectionLivelinessController = CNSCommClient._ConnectionLivelinessController(
            dead=False, on_disconnect=self.on_disconnect
        )

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

        self.subscribe(key, data_type, callback) # type: ignore

    def get(self, key: CommPath | str, data_type: type[T]) -> T | None:
        """
        Retrieve and deserialize sendable by key.

        Args:
            key: Key to retrieve.
            data_type: Sendable type to deserialize to.

        Returns:
            Sendable or None if not found.
        """

        if not self.client:
            _Logger().error("Cannot get data: client is not started")
            return None
        try:
            raw = self.client.get(str(key))
            self._dead.dead = False
        except (ConnectionError, TimeoutError) as e:
            _Logger().error(f"Cannot get {key}: {e}")
            self._dead.dead = True
            return None
        if raw is None:
            return None
        try:
            if isinstance(raw, dict):
                data = raw
            else:
                data = json.loads(raw)
            if data_type:
                return data_type(**data)
        except (orjson.JSONDecodeError, ValidationError, KeyError, TypeError, websockets.exceptions.ConnectionClosedError):
            pass
        return None

    def multi_get(self, requests: list[GetRequest]):
        """
        Retrieve and deserialize multiple sendables by a list of GetRequest objects.

        Args:
            requests: List of GetRequest objects.

        Returns:
            List of sendables or None for each request if not found.
        """
        if not self.client:
            _Logger().error("Cannot multi_get: client is not started")
            return [None] * len(requests)
        
        results = []
        for req in requests:
            try:
                raw = self.client.get(str(req.key))
                self._dead.dead = False
                if raw is None:
                    results.append(None)
                    continue
                if isinstance(raw, dict):
                    data = raw
                else:
                    data = json.loads(raw)
                if req.data_type:
                    results.append(req.data_type(**data))
                else:
                    results.append(None)
            except (ConnectionError, TimeoutError, orjson.JSONDecodeError, ValidationError, KeyError, TypeError, websockets.exceptions.ConnectionClosedError):
                results.append(None)
        return results

    def get_keys(self) -> list[str]:
        """
        Gets all keys in the CNS database.

        Returns:
            List of keys.
        """

        if not self.client:
            _Logger().error("Cannot get keys: client is not started")
            return []
        try:
            keys = self.client.topics()
            self._dead.dead = False
            return keys if keys else []
        except (ConnectionError, TimeoutError, websockets.exceptions.ConnectionClosedError) as e:
            _Logger().error(f"Cannot get keys: {e}")
            self._dead.dead = True
            return []

    def get_raw(self, key: CommPath | str) -> dict | None:
        """
        Retrieve the raw JSON for a key, ignoring the sendable deserialization.

        Args:
            key: Key to retrieve.

        Returns:
            Raw JSON value or None if not found.
        """
        if not self.client:
            _Logger().error("Cannot get raw: client is not started")
            return None
        try:
            raw = self.client.get(str(key))
            self._dead.dead = False
            if isinstance(raw, dict):
                return raw
            elif raw is not None:
                return orjson.loads(raw) if isinstance(raw, (str, bytes)) else None
            return None
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
        if not self.client:
            _Logger().error("Cannot get all raw: client is not started")
            return None
        try:
            # Get all keys from CNS
            keys = self.client.topics()
            if not keys:
                self._dead.dead = False
                return {}

            # Retrieve all values
            result = {}
            for key in keys:
                value = self.client.get(key)
                if value:
                    if isinstance(value, dict):
                        result[key] = value
                    else:
                        result[key] = orjson.loads(value) if isinstance(value, (str, bytes)) else value
            self._dead.dead = False
            return result
        except (ConnectionError, TimeoutError, websockets.exceptions.ConnectionClosedError) as e:
            _Logger().error(f"Cannot get all raw: {e}")
            self._dead.dead = True
            return None

    def _apply(self, key: CommPath | str, sendable: BaseSendable | SendableGenerator):
        if not self.client:
            _Logger().error(f"Cannot publish/set to {key}: client is not started")
            return

        if isinstance(sendable, SendableGenerator):
            sendable = sendable.generate_sendable()

        data = sendable.get_dict()
        try:
            if sendable.timeout:
                self.client.set(str(key), data, timeout=int(sendable.timeout * 1000))
            else:
                self.client.set(str(key), data)
            self._dead.dead = False
        except (ConnectionError, TimeoutError, ValueError, AttributeError) as e:
            _Logger().error(f"Cannot publish/set to {key}: {e}")
            self._dead.dead = True

    def _apply_multi(self, keys: list[CommPath | str], sendables: list[BaseSendable | SendableGenerator]):
        if not self.client:
            _Logger().error("Cannot multi-set: client is not started")
            return

        if len(keys) != len(sendables):
            _Logger().error("Keys and sendables must have the same length")
            return

        try:
            for key, sendable in zip(keys, sendables, strict=False):
                if isinstance(sendable, SendableGenerator):
                    sendable = sendable.generate_sendable()  # noqa: PLW2901
                data = sendable.get_dict()
                # TODO: CNS doesn't support timeouts natively
                if sendable.timeout:
                    _Logger().warning(f"CNS does not support timeouts. Ignoring timeout for {key}")
                self.client.set(str(key), data)
            self._dead.dead = False
        except (ConnectionError, TimeoutError, ValueError, AttributeError) as e:
            _Logger().error(f"Cannot multi-set: {e}")
            self._dead.dead = True

    def set(self, key: CommPath | str, sendable: BaseSendable | SendableGenerator) -> None:
        """
        Set sendable in the CNS database.

        Args:
            key: Key to set
            sendable: Sendable to set
        """

        self._apply(key, sendable)

    def multi_set(self, requests: list[SetRequest]) -> None:
        """
        Set multiple sendables in the CNS database.

        Args:
            requests: Sequence of SetRequest objects.
        """

        self._apply_multi([x.key for x in requests], [x.data for x in requests])

    def publish(self, key: CommPath | str, sendable: BaseSendable | SendableGenerator) -> None:
        """
        Publish sendable in the CNS Pub/Sub client.

        Args:
            key: Key to publish to
            sendable: Sendable to publish
        """

        self._apply(key, sendable)

    def subscribe(self, key: CommPath | str, data_type: type[T], callback: Callable[[str, T | None], None]) -> None:
        """
        Subscribe to a topic.

        Args:
            key: Key to subscribe to.
            data_type: Sendable type to deserialize to.
            callback: Callback when data is received.
        """

        def sub_callback(topic: str, data: JSONType):
            try:
                if data:
                    sendable = data_type(**data)
                    callback(topic, sendable)
                else:
                    callback(topic, None)
            except (ValidationError, TypeError) as ex:
                _Logger().error(f"Failed to deserialize data for topic {topic}: {ex}")

        if isinstance(key, CommPath):
            key = str(key)
        with self._lock:
            key_str = str(key)
            if self.client:
                try:
                    self.client.subscribe(key_str, sub_callback)
                    self.hooks.append((key_str, data_type, callback))
                    self._dead.dead = False
                except (ConnectionError, TimeoutError) as e:
                    _Logger().error(f"Cannot subscribe to {key_str}: {e}")
                    self._dead.dead = True
            else:
                _Logger().error(f"Can't subscribe to {key}, client is not running")

    def wipeall(self) -> None:
        """Delete all keys in the CNS database."""
        if not self.client:
            _Logger().error("Cannot flush database: client is not started")
            return
        try:
            self.client.flushdb()
            self._dead.dead = False
        except (ConnectionError, TimeoutError) as e:
            _Logger().error(f"Cannot flush database: {e}")
            self._dead.dead = True

    def delete(self, key: CommPath | str) -> None:
        """
        Delete a key from the CNS database.

        Args:
            key: Key to delete.
        """

        if not self.client:
            _Logger().error("Cannot delete: client is not started")
            return
        try:
            # CNS delete is done by setting to None or empty
            self.client.delete(str(key))
            self._dead.dead = False
        except (ConnectionError, TimeoutError) as e:
            _Logger().error(f"Cannot delete {key}: {e}")
            self._dead.dead = True

    def connect(self) -> None:
        """Connect to the CNS server."""

        if self._flag_robot:
            if not self._client_id:
                self._client_id = f"robot~{self._flag_robot}-{str(uuid.uuid4())[:8]}"
        else:
            if not self._client_id:
                self._client_id = f"client~KevinbotLib-{str(uuid.uuid4())[:8]}"

        if self.client:
            try:
                self.client.disconnect()
            except Exception:
                pass

        self.client = CNSClient(
            url=f"ws://{self._host}:{self._port}/cns",
            client_id=self._client_id,
        )
        try:
            self.client.connect()
            # TODO: CNS doesn't have a ping method, so we just check if client exists
            self._dead.dead = False
            if self.on_connect:
                self.on_connect()
        except (ConnectionError, TimeoutError, socket.gaierror, OSError) as e:
            _Logger().error(f"CNS connection error: {e!r}")
            self._dead.dead = True
            self.client = None
            if self.on_disconnect:
                self.on_disconnect()
            return

    def is_connected(self) -> bool:
        """
        Check if the CNS connection is established.

        Returns:
            Is the connection established?
        """
        return self.client is not None and not self._dead.dead

    def get_latency(self) -> float | None:
        """
        Measure the round-trip latency to the CNS server in milliseconds.

        Returns:
            Latency in milliseconds or None if not connected.
        """
        if not self.client:
            return None
        try:
            seconds = self.client.ping()
            if not seconds:
                return None

            self._dead.dead = False
            return seconds * 1000
        except (ConnectionError, TimeoutError) as e:
            _Logger().error(f"Cannot measure latency: {e}")
            self._dead.dead = True
            return None

    def wait_until_connected(self, timeout: float = 5.0):
        """
        Wait until the CNS connection is established.

        Args:
            timeout: Timeout in seconds. Defaults to 5.0 seconds.
        """

        start_time = time.time()
        while not self.client or self._dead.dead:
            if time.time() > start_time + timeout:
                self._dead.dead = True
                msg = "The connection timed out"
                raise kevinbotlib.exceptions.HandshakeTimeoutException(msg)
            time.sleep(0.02)

    def close(self):
        """Close the CNS connection and stop the threads."""
        if self.client:
            self.client.disconnect()
            self.client = None
        if self.on_disconnect:
            self.on_disconnect()

    def reset_connection(self):
        """Reset the connection to the CNS server"""
        _Logger().info("Resetting CNS connection...")
        self.close()
        
        # Just reconnect with the existing client (which will recreate loop/thread if needed)
        # Don't create a new client - that would lose the persistent client_id
        try:
            self.connect()
            _Logger().info("CNS connection reset successful")
        except Exception as e:
            _Logger().error(f"Failed to reset CNS connection: {e!r}")

    @property
    def host(self) -> str:
        """
        Get the currently connected server host.

        Returns:
            Server host.
        """

        return self._host

    @property
    def port(self) -> int:
        """
        Get the currently connected server port.

        Returns:
            Server port.
        """
        return self._port

    @host.setter
    def host(self, value: str) -> None:
        self._host = value
        self.reset_connection()

    @port.setter
    def port(self, value: int) -> None:
        self._port = value
        self.reset_connection()

    @property
    def timeout(self) -> float:
        """
        Get the current server timeout.

        Returns:
            Server timeout in seconds.
        """
        return self._timeout
