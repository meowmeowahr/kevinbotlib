import json
import threading
import time
from collections.abc import Callable
from typing import ClassVar, TypeVar, final

import orjson
import redis
import redis.cache
import redis.exceptions
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

__all__ = ["RedisCommClient"]

from kevinbotlib.util import is_unix_socket

T = TypeVar("T", bound=BaseSendable)


class RedisCommClient(AbstractSetGetNetworkClient, AbstractPubSubNetworkClient):
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
        port: int = 6379,
        unix_socket: str | None = None,
        db: int = 0,
        timeout: float = 2,
        on_connect: Callable[[], None] | None = None,
        on_disconnect: Callable[[], None] | None = None,
    ) -> None:
        """
        Initialize a Redis Communication Client.

        Args:
            host: Host of the Redis server.
            port: Port of the Redis server.
            unix_socket: Optional UNIX socket path. A UNIX socket path is preferred over TCP.
            db: Database number to use.
            timeout: Socket timeout in seconds.
            on_connect: Connection callback.
            on_disconnect: Disconnection callback.
        """

        self.redis: redis.Redis | None = None
        self._host = host
        self._port = port
        self._unix_socket = unix_socket
        self._db = db
        self._timeout = timeout
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.running = False
        self.sub_thread: threading.Thread | None = None
        self.hooks: list[tuple[str, type[BaseSendable], Callable[[str, BaseSendable | None], None]]] = []

        self.pubsub: redis.client.PubSub | None = None
        self.sub_callbacks: dict[str, tuple[type[BaseSendable], Callable[[str, BaseSendable], None]]] = {}
        self._lock = threading.Lock()
        self._listener_thread: threading.Thread | None = None
        self._dead: RedisCommClient._ConnectionLivelinessController = RedisCommClient._ConnectionLivelinessController(
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

        self.hooks.append((str(key), data_type, callback))  # type: ignore

    def get(self, key: CommPath | str, data_type: type[T]) -> T | None:
        """
        Retrieve and deserialize sendable by key.

        Args:
            key: Key to retrieve.
            data_type: Sendable type to deserialize to.

        Returns:
            Sendable or None if not found.
        """

        if not self.redis:
            _Logger().error("Cannot get data: client is not started")
            return None
        try:
            raw = self.redis.get(str(key))
            self._dead.dead = False
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            _Logger().error(f"Cannot get {key}: {e}")
            self._dead.dead = True
            return None
        if raw is None:
            return None
        try:
            data = json.loads(raw)
            if data_type:
                return data_type(**data)
        except (orjson.JSONDecodeError, ValidationError, KeyError):
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
        if not self.redis:
            _Logger().error("Cannot multi_get: client is not started")
            return [None] * len(requests)
        keys = [str(req.key) for req in requests]
        try:
            raw_values = self.redis.mget(keys)
            self._dead.dead = False
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            _Logger().error(f"Cannot multi_get: {e}")
            self._dead.dead = True
            return [None] * len(requests)
        results = []
        for raw, req in zip(raw_values, requests, strict=False):
            if raw is None:
                results.append(None)
                continue
            try:
                data = json.loads(raw)
                if req.data_type:
                    results.append(req.data_type(**data))
                else:
                    results.append(None)
            except (orjson.JSONDecodeError, ValidationError, KeyError):
                results.append(None)
        return results

    def get_keys(self) -> list[str]:
        """
        Gets all keys in the Redis database.

        Returns:
            List of keys.
        """

        if not self.redis:
            _Logger().error("Cannot get keys: client is not started")
            return []
        try:
            keys = self.redis.keys("*")
            self._dead.dead = False
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            _Logger().error(f"Cannot get keys: {e}")
            self._dead.dead = True
            return []
        else:
            return keys

    def get_raw(self, key: CommPath | str) -> dict | None:
        """
        Retrieve the raw JSON for a key, ignoring the sendable deserialization.

        Args:
            key: Key to retrieve.

        Returns:
            Raw JSON value or None if not found.
        """

        if not self.redis:
            _Logger().error("Cannot get raw: client is not started")
            return None
        try:
            raw = self.redis.get(str(key))
            self._dead.dead = False
            return orjson.loads(raw) if raw else None
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            _Logger().error(f"Cannot get raw {key}: {e}")
            self._dead.dead = True
            return None

    def get_all_raw(self) -> dict[str, dict] | None:
        """
        Retrieve all raw JSON values as a dictionary of a key to raw value. May have slow performance.

        Returns:
            Dictionary of a key to raw value or None if not found.
        """
        if not self.redis:
            _Logger().error("Cannot get all raw: client is not started")
            return None
        try:
            # Get all keys from Redis
            keys = self.redis.keys("*")
            if not keys:
                self._dead.dead = False
                return {}

            # Retrieve all values using mget for efficiency
            values = self.redis.mget(keys)
            self._dead.dead = False

            # Construct result dictionary, decoding JSON values
            result = {}
            for key, value in zip(keys, values, strict=False):
                if value:
                    result[key] = orjson.loads(value)
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            _Logger().error(f"Cannot get all raw: {e}")
            self._dead.dead = True
            return None
        else:
            return result

    def _apply(self, key: CommPath | str, sendable: BaseSendable | SendableGenerator, *, pub_mode: bool = False):
        if not self.running or not self.redis:
            _Logger().error(f"Cannot publish/set to {key}: client is not started")
            return

        if isinstance(sendable, SendableGenerator):
            sendable = sendable.generate_sendable()

        data = sendable.get_dict()
        kwargs = None
        try:
            kwargs = self.redis.connection_pool.connection_kwargs
            if pub_mode:
                if sendable.timeout:
                    _Logger().warning("Publishing a Sendable with a timeout. Pub/Sub does not support this.")
                self.redis.publish(str(key), orjson.dumps(data))
            elif sendable.timeout:
                self.redis.set(str(key), orjson.dumps(data), px=int(sendable.timeout * 1000))
            else:
                self.redis.set(str(key), orjson.dumps(data))
            self._dead.dead = False
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, ValueError, AttributeError) as e:
            _Logger().error(f"Cannot publish/set to {key}: {e}")
            if (
                (not self.redis)
                or (not self.redis.connection_pool)
                or (kwargs == self.redis.connection_pool.connection_kwargs)
            ):
                self._dead.dead = True
            else:
                _Logger().warning("Connection kwargs changed while getting ping to server. Connection may not be dead.")

    def _apply_multi(self, keys: list[CommPath | str], sendables: list[BaseSendable | SendableGenerator]):
        if not self.running or not self.redis:
            _Logger().error("Cannot multi-set: client is not started")
            return

        if len(keys) != len(sendables):
            _Logger().error("Keys and sendables must have the same length")
            return

        try:
            pipe = self.redis.pipeline()
            for key, sendable in zip(keys, sendables, strict=False):
                if isinstance(sendable, SendableGenerator):
                    sendable = sendable.generate_sendable()  # noqa: PLW2901
                data = sendable.get_dict()
                if sendable.timeout:
                    pipe.set(str(key), orjson.dumps(data), px=int(sendable.timeout * 1000))
                else:
                    pipe.set(str(key), orjson.dumps(data))
            pipe.execute()
            self._dead.dead = False
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, ValueError, AttributeError) as e:
            _Logger().error(f"Cannot multi-set: {e}")
            self._dead.dead = True

    def set(self, key: CommPath | str, sendable: BaseSendable | SendableGenerator) -> None:
        """
        Set sendable in the Redis database.

        Args:
            key: Key to set
            sendable: Sendable to set
        """

        self._apply(key, sendable, pub_mode=False)

    def multi_set(self, requests: list[SetRequest]) -> None:
        """
        Set multiple sendables in the Redis database.

        Args:
            requests: Sequence of SetRequest objects.
        """

        self._apply_multi([x.key for x in requests], [x.data for x in requests])

    def publish(self, key: CommPath | str, sendable: BaseSendable | SendableGenerator) -> None:
        """
        Publish sendable in the Redis Pub/Sub client.

        Args:
            key: Key to publish to
            sendable: Sendable to publish
        """

        self._apply(key, sendable, pub_mode=True)

    def _listen_loop(self):
        if not self.pubsub:
            return
        try:
            while True:
                for message in self.pubsub.listen():
                    if not self.running:
                        break
                    if message["type"] == "message":
                        channel = message["channel"]
                        try:
                            data = orjson.loads(message["data"])
                            callback = self.sub_callbacks.get(channel)
                            if callback:
                                callback[1](channel, callback[0](**data))
                        except Exception as e:  # noqa: BLE001
                            _Logger().error(f"Failed to process message: {e!r}")
                    self._dead.dead = False
                time.sleep(1)  # 1-second delay if there are no subscriptions
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, ValueError, AttributeError):
            self._dead.dead = True
        _Logger().warning("Listener loop ended")

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
        with self._lock:
            key_str = str(key)
            self.sub_callbacks[key_str] = (data_type, callback)  # type: ignore
            if self.pubsub:
                try:
                    self.pubsub.subscribe(key_str)
                except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
                    _Logger().error(f"Cannot subscribe to {key_str}: {e}")
            else:
                _Logger().error(f"Can't subscribe to {key}, Pub/Sub is not running")

    def wipeall(self) -> None:
        """Delete all keys in the Redis database."""

        if not self.redis:
            _Logger().error("Cannot wipe all: client is not started")
            return
        try:
            self.redis.flushdb()
            self.redis.flushall()
            self._dead.dead = False
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            _Logger().error(f"Cannot wipe all: {e}")
            self._dead.dead = True

    def delete(self, key: CommPath | str) -> None:
        """
        Delete a key from the Redis database.

        Args:
            key: Key to delete.
        """

        if not self.redis:
            _Logger().error("Cannot delete: client is not started")
            return
        try:
            self.redis.delete(str(key))
            self._dead.dead = False
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            _Logger().error(f"Cannot delete {key}: {e}")
            self._dead.dead = True

    def _start_hooks(self) -> None:
        if not self.running:
            self.running = True
            self.sub_thread = threading.Thread(target=self._run_hooks, daemon=True, name="KevinbotLib.Redis.Hooks")
            self.sub_thread.start()

    def _run_hooks(self):
        """Run the pubsub listener in a separate thread."""
        previous_values = {}
        while True:
            # update previous values with hook keys
            try:
                if not self.running:
                    break
                if not self.redis:
                    time.sleep(0.01)
                    continue
                keys = [key for key, _, _ in self.hooks]
                # Initialize previous_values for new keys
                for key in keys:
                    if key not in previous_values:
                        previous_values[key] = None

                    if not redis:
                        return

                # Use mget to fetch all values at once
                messages = self.redis.mget(keys)
                key_to_message = dict(zip(keys, messages, strict=False))

                for key, message in key_to_message.items():
                    if message != previous_values[key]:
                        # Call the hook for all hooks matching this key
                        for ckey, data_type, callback in self.hooks:
                            if ckey != key:
                                continue
                            try:
                                raw = message
                                if raw:
                                    data = orjson.loads(raw)
                                    if data["did"] == data_type(**data).data_id:
                                        sendable = self.SENDABLE_TYPES[data["did"]](**data)
                                        callback(ckey, sendable)
                                else:
                                    callback(ckey, None)
                            except (orjson.JSONDecodeError, ValidationError, KeyError):
                                pass
                    previous_values[key] = message
                self._dead.dead = False
            except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
                self._dead.dead = True
            except (AttributeError, ValueError) as e:
                _Logger().error(f"Something went wrong while processing hooks: {e!r}")
            if not self.running:
                break
            time.sleep(0.01)

    def connect(self) -> None:
        """Connect to the Redis server."""

        if self._unix_socket and is_unix_socket(self._unix_socket):
            self.redis = redis.Redis(
                unix_socket_path=self._unix_socket,
                decode_responses=True,
                socket_timeout=self._timeout,
                protocol=3,
                # cache_config=redis.cache.CacheConfig(),
            )
        else:
            self.redis = redis.Redis(
                host=self._host,
                port=self._port,
                db=self._db,
                decode_responses=True,
                socket_timeout=self._timeout,
                protocol=3,
                # cache_config=redis.cache.CacheConfig(),
            )
        self.pubsub = self.redis.pubsub()
        self._start_hooks()
        try:
            self.redis.ping()
            self._dead.dead = False
            if self.on_connect:
                self.on_connect()
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            _Logger().error(f"Redis connection error: {e}")
            self._dead.dead = True
            self.redis = None
            if self.on_disconnect:
                self.on_disconnect()
            return

        # subscribe
        for sub in self.sub_callbacks:
            self.pubsub.subscribe(sub)

        self._listener_thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="KevinbotLib.Redis.Listener"
        )
        self._listener_thread.start()

    def is_connected(self) -> bool:
        """
        Check if the Redis connection is established.

        Returns:
            Is the connection established?
        """
        return self.redis is not None and self.redis.connection_pool is not None and not self._dead.dead

    def get_latency(self) -> float | None:
        """
        Measure the round-trip latency to the Redis server in milliseconds.

        Returns:
            Latency in milliseconds or None if not connected.
        """

        if not self.redis:
            return None
        kwargs = None
        try:
            kwargs = self.redis.connection_pool.connection_kwargs
            start_time = time.time()
            self.redis.ping()
            end_time = time.time()
            return (end_time - start_time) * 1000  # Convert to milliseconds
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            _Logger().error(f"Cannot measure latency: {e}")
            if (
                (not self.redis)
                or (not self.redis.connection_pool)
                or (kwargs == self.redis.connection_pool.connection_kwargs)
            ):
                self._dead.dead = True
            else:
                _Logger().warning("Connection kwargs changed while getting ping to server. Connection may not be dead.")
            return None

    def wait_until_connected(self, timeout: float = 5.0):
        """
        Wait until the Redis connection is established.

        Args:
            timeout: Timeout in seconds. Defaults to 5.0 seconds.
        """

        start_time = time.time()
        while not self.redis or not self.redis.ping():
            if time.time() > start_time + timeout:
                self._dead.dead = True
                msg = "The connection timed out"
                raise kevinbotlib.exceptions.HandshakeTimeoutException(msg)
            time.sleep(0.02)

    def close(self):
        """Close the Redis connection and stop the pubsub thread."""
        self.running = False
        if self.redis:
            self.redis.close()
            self.redis = None
        if self.on_disconnect:
            self.on_disconnect()

    @final
    def _redis_connection_check(self):
        try:
            if not self.redis:
                return
            self.redis.ping()
            if self.on_connect:
                self.on_connect()

            if not self._listener_thread or not self._listener_thread.is_alive():
                self._listener_thread = threading.Thread(
                    target=self._listen_loop, daemon=True, name="KevinbotLib.Redis.Listener"
                )
                self._listener_thread.start()
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, ValueError, AttributeError):
            self._dead.dead = True
            return

    def reset_connection(self):
        """Reset the connection to the Redis server"""
        if self.running:
            # get subs
            subscriptions = {}
            if self.pubsub:
                subscriptions = self.pubsub.channels

            self.close()

            if self._unix_socket and is_unix_socket(self._unix_socket):
                self.redis = redis.Redis(
                    unix_socket_path=self._unix_socket,
                    decode_responses=True,
                    socket_timeout=self._timeout,
                    protocol=3,
                    # cache_config=redis.cache.CacheConfig(),
                )
            else:
                self.redis = redis.Redis(
                    host=self._host,
                    port=self._port,
                    db=self._db,
                    decode_responses=True,
                    socket_timeout=self._timeout,
                    protocol=3,
                    # cache_config=redis.cache.CacheConfig(),
                )
            self.pubsub = self.redis.pubsub()
            for sub in subscriptions.values():
                if sub is None:
                    continue
                try:
                    self.pubsub.subscribe(sub)
                except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
                    self._dead.dead = True
                    _Logger().warning(f"Failed to re-subscribe to {sub}, client is not connected")

            self._start_hooks()

            self._listener_thread = threading.Thread(
                target=self._listen_loop, daemon=True, name="KevinbotLib.Redis.Listener"
            )
            self._listener_thread.start()

            checker = threading.Thread(target=self._redis_connection_check, daemon=True)
            checker.name = "KevinbotLib.Redis.ConnCheck"
            checker.start()

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
        if self.redis:
            self.redis.connection_pool.connection_kwargs["host"] = value
        self.reset_connection()

    @port.setter
    def port(self, value: int) -> None:
        self._port = value
        if self.redis:
            self.redis.connection_pool.connection_kwargs["port"] = value
        self.reset_connection()

    @property
    def unix_socket(self) -> str | None:
        return self._unix_socket

    @unix_socket.setter
    def unix_socket(self, value: str | None) -> None:
        self._unix_socket = value
        if self.redis:
            self.redis.connection_pool.connection_kwargs["path"] = value
        self.reset_connection()

    @property
    def timeout(self) -> float:
        """
        Get the current server timeout.

        Returns:
            Server timeout in seconds.
        """
        return self._timeout
