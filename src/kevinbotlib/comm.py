import json
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, ClassVar, TypeVar, final

import orjson
import redis
import redis.exceptions
from pydantic import BaseModel, ValidationError

import kevinbotlib.exceptions
from kevinbotlib.logger import Logger as _Logger


class BaseSendable(BaseModel, ABC):
    """
    The base for all of KevinbotLib's sendables.

    _**What is a sendable?**_

    A sendable is a basic unit of data that can be transported through the `KevinbotCommClient` and server
    """

    timeout: float | None = None
    data_id: str = "kevinbotlib.dtype.null"
    """Internally used to differentiate sendable types"""
    flags: list[str] = []
    struct: dict[str, Any] = {}
    """Data structure _suggestion_ for use in dashboard applications"""

    def get_dict(self) -> dict:
        """Return the sendable in dictionary form

        Returns:
            dict: The sendable data
        """
        return {
            "timeout": self.timeout,
            "value": None,
            "did": self.data_id,
            "struct": self.struct,
        }


class SendableGenerator(ABC):
    """
    Abstract class for a function capable of being sent over `KevinbotCommClient`
    """

    @abstractmethod
    def generate_sendable(self) -> BaseSendable:
        """Abstract method to generate a sendable

        Returns:
            BaseSendable: The returned sendable
        """


class IntegerSendable(BaseSendable):
    value: int
    """Value to send"""
    data_id: str = "kevinbotlib.dtype.int"
    """Internally used to differentiate sendable types"""
    struct: dict[str, Any] = {"dashboard": [{"element": "value", "format": "raw"}]}
    """Data structure _suggestion_ for use in dashboard applications"""

    def get_dict(self) -> dict:
        """Return the sendable in dictionary form

        Returns:
            dict: The sendable data
        """
        data = super().get_dict()
        data["value"] = self.value
        return data


class BooleanSendable(BaseSendable):
    value: bool
    """Value to send"""
    data_id: str = "kevinbotlib.dtype.bool"
    """Internally used to differentiate sendable types"""
    struct: dict[str, Any] = {"dashboard": [{"element": "value", "format": "raw"}]}
    """Data structure _suggestion_ for use in dashboard applications"""

    def get_dict(self) -> dict:
        """Return the sendable in dictionary form

        Returns:
            dict: The sendable data
        """
        data = super().get_dict()
        data["value"] = self.value
        return data


class StringSendable(BaseSendable):
    value: str
    """Value to send"""
    data_id: str = "kevinbotlib.dtype.str"
    """Internally used to differentiate sendable types"""
    struct: dict[str, Any] = {"dashboard": [{"element": "value", "format": "raw"}]}
    """Data structure _suggestion_ for use in dashboard applications"""

    def get_dict(self) -> dict:
        """Return the sendable in dictionary form

        Returns:
            dict: The sendable data
        """
        data = super().get_dict()
        data["value"] = self.value
        return data


class FloatSendable(BaseSendable):
    value: float
    """Value to send"""
    data_id: str = "kevinbotlib.dtype.float"
    """Internally used to differentiate sendable types"""
    struct: dict[str, Any] = {"dashboard": [{"element": "value", "format": "raw"}]}
    """Data structure _suggestion_ for use in dashboard applications"""

    def get_dict(self) -> dict:
        """Return the sendable in dictionary form

        Returns:
            dict: The sendable data
        """
        data = super().get_dict()
        data["value"] = self.value
        return data


class AnyListSendable(BaseSendable):
    value: list
    """Value to send"""
    data_id: str = "kevinbotlib.dtype.list.any"
    """Internally used to differentiate sendable types"""
    struct: dict[str, Any] = {"dashboard": [{"element": "value", "format": "raw"}]}
    """Data structure _suggestion_ for use in dashboard applications"""

    def get_dict(self) -> dict:
        """Return the sendable in dictionary form

        Returns:
            dict: The sendable data
        """
        data = super().get_dict()
        data["value"] = self.value
        return data


class DictSendable(BaseSendable):
    value: dict
    """Value to send"""
    data_id: str = "kevinbotlib.dtype.dict"
    """Internally used to differentiate sendable types"""
    struct: dict[str, Any] = {"dashboard": [{"element": "value", "format": "raw"}]}
    """Data structure _suggestion_ for use in dashboard applications"""

    def get_dict(self) -> dict:
        """Return the sendable in dictionary form

        Returns:
            dict: The sendable data
        """
        data = super().get_dict()
        data["value"] = self.value
        return data


class BinarySendable(BaseSendable):
    value: bytes
    """Value to send"""
    data_id: str = "kevinbotlib.dtype.bin"
    """Internally used to differentiate sendable types"""
    struct: dict[str, Any] = {"dashboard": [{"element": "value", "format": "limit:1024"}]}
    """Data structure _suggestion_ for use in dashboard applications"""

    def get_dict(self) -> dict:
        """Return the sendable in dictionary form

        Returns:
            dict: The sendable data
        """
        data = super().get_dict()
        data["value"] = self.value.decode("utf-8")
        return data


T = TypeVar("T", bound=BaseSendable)


class CommPath:
    def __init__(self, path: "str | CommPath") -> None:
        if isinstance(path, CommPath):
            path = path.path
        self._path = path

    def __truediv__(self, new: str):
        return CommPath(self._path.rstrip("/") + "/" + new.lstrip("/"))

    def __str__(self) -> str:
        return self._path

    @property
    def path(self) -> str:
        return self._path


class RedisCommClient:
    SENDABLE_TYPES: ClassVar = {
        "kevinbotlib.dtype.int": IntegerSendable,
        "kevinbotlib.dtype.bool": BooleanSendable,
        "kevinbotlib.dtype.str": StringSendable,
        "kevinbotlib.dtype.float": FloatSendable,
        "kevinbotlib.dtype.list.any": AnyListSendable,
        "kevinbotlib.dtype.dict": DictSendable,
        "kevinbotlib.dtype.bin": BinarySendable,
    }

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        on_connect: Callable[[], None] | None = None,
        on_disconnect: Callable[[], None] | None = None,
    ) -> None:
        """Initialize Redis client with connection parameters."""
        self.redis = None
        self._host = host
        self._port = port
        self._db = db
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.running = False
        self.sub_thread: threading.Thread | None = None
        self.hooks: list[tuple[str, type[BaseSendable], Callable[[str, BaseSendable], None]]] = []

        self.pubsub = None
        self.sub_callbacks: dict[str, tuple[type[BaseSendable], Callable[[str, BaseSendable], None]]] = {}
        self._lock = threading.Lock()
        self._listener_thread: threading.Thread | None = None
        self._dead = False

    def register_type(self, data_type: type[BaseSendable]):
        self.SENDABLE_TYPES[data_type.model_fields["data_id"].default] = data_type
        _Logger().trace(
            f"Registered data type of id {data_type.model_fields['data_id'].default} as {data_type.__name__}"
        )

    def add_hook(self, key: CommPath | str, data_type: type[T], callback: Callable[[str, T], None]) -> None:
        """Add a callback to be triggered when a sendable of data_type is set for key."""
        self.hooks.append((str(key), data_type, callback))  # type: ignore

    def get(self, key: CommPath | str, data_type: type[T]) -> T | None:
        """Retrieve and deserialize a sendable by key."""
        if not self.redis:
            _Logger().error("Cannot get data: client is not started")
            return None
        try:
            raw = self.redis.get(str(key))
            self._dead = False
        except redis.exceptions.ConnectionError as e:
            _Logger().error(f"Cannot get {key}: {e}")
            self._dead = True
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

    def get_keys(self) -> list[str]:
        """Return a list of all keys in the Redis database."""
        if not self.redis:
            _Logger().error("Cannot get keys: client is not started")
            return []
        try:
            keys = self.redis.keys("*")
            self._dead = False
        except redis.exceptions.ConnectionError as e:
            _Logger().error(f"Cannot get keys: {e}")
            self._dead = True
            return []
        else:
            return keys

    def get_raw(self, key: CommPath | str) -> dict | None:
        """Retrieve the raw JSON for a key."""
        if not self.redis:
            _Logger().error("Cannot get raw: client is not started")
            return None
        try:
            raw = self.redis.get(str(key))
            self._dead = False
            return orjson.loads(raw) if raw else None
        except redis.exceptions.ConnectionError as e:
            _Logger().error(f"Cannot get raw {key}: {e}")
            self._dead = True
            return None

    def get_all_raw(self) -> dict[str, dict] | None:
        """Retrieve all raw JSON values as a dictionary of key to raw value."""
        if not self.redis:
            _Logger().error("Cannot get all raw: client is not started")
            return None
        try:
            # Get all keys from Redis
            keys = self.redis.keys("*")
            if not keys:
                self._dead = False
                return {}

            # Retrieve all values using mget for efficiency
            values = self.redis.mget(keys)
            self._dead = False

            # Construct result dictionary, decoding JSON values
            result = {}
            for key, value in zip(keys, values, strict=False):
                if value:
                    result[key] = orjson.loads(value)
        except redis.exceptions.ConnectionError as e:
            _Logger().error(f"Cannot get all raw: {e}")
            self._dead = True
            return None
        else:
            return result

    def _apply(self, key: CommPath | str, sendable: BaseSendable | SendableGenerator, *, pub_mode: bool = False):
        """Set a sendable in the Redis database."""
        if not self.running or not self.redis:
            _Logger().error(f"Cannot publish to {key}: client is not started")
            return

        if isinstance(sendable, SendableGenerator):
            sendable = sendable.generate_sendable()

        data = sendable.get_dict()
        try:
            if pub_mode:
                if sendable.timeout:
                    _Logger().warning("Publishing a Sendable with a timeout. Pub/Sub does not support this.")
                self.redis.publish(str(key), orjson.dumps(data))
            elif sendable.timeout:
                self.redis.set(str(key), orjson.dumps(data), px=int(sendable.timeout * 1000))
            else:
                self.redis.set(str(key), orjson.dumps(data))
            self._dead = False
        except (redis.exceptions.ConnectionError, ValueError, AttributeError) as e:
            _Logger().error(f"Cannot publish to {key}: {e}")
            self._dead = True

    def set(self, key: CommPath | str, sendable: BaseSendable | SendableGenerator) -> None:
        self._apply(key, sendable, pub_mode=False)

    def publish(self, key: CommPath | str, sendable: BaseSendable | SendableGenerator) -> None:
        """Publish a sendable in the Redis database."""
        self._apply(key, sendable, pub_mode=True)

    def _listen_loop(self):
        if not self.pubsub:
            return
        try:
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
                self._dead = False
        except (redis.exceptions.ConnectionError, ValueError, AttributeError):
            self._dead = True
        _Logger().warning("Listener loop ended")

    def subscribe(self, key: CommPath | str, data_type: type[T], callback: Callable[[str, T], None]) -> None:
        if isinstance(key, CommPath):
            key = str(key)
        with self._lock:
            key_str = str(key)
            self.sub_callbacks[key_str] = (data_type, callback)  # type: ignore
            if self.pubsub:
                self.pubsub.subscribe(key_str)
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
            self._dead = False
        except redis.exceptions.ConnectionError as e:
            _Logger().error(f"Cannot wipe all: {e}")
            self._dead = True

    def delete(self, key: CommPath | str) -> None:
        """Delete a key from the Redis database."""
        if not self.redis:
            _Logger().error("Cannot delete: client is not started")
            return
        try:
            self.redis.delete(str(key))
            self._dead = False
        except redis.exceptions.ConnectionError as e:
            _Logger().error(f"Cannot delete {key}: {e}")
            self._dead = True

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
                for key, _, _ in self.hooks:
                    if key not in previous_values:
                        previous_values[key] = None
                    if not redis:
                        continue
                    message = self.redis.get(key)
                    if message != previous_values[key]:
                        # Call the hook
                        for ckey, data_type, callback in self.hooks:
                            try:
                                raw = self.redis.get(ckey)
                                if raw:
                                    data = orjson.loads(raw)
                                    if data["did"] == data_type(**data).data_id:
                                        sendable = self.SENDABLE_TYPES[data["did"]](**data)
                                        callback(ckey, sendable)
                            except (orjson.JSONDecodeError, ValidationError, KeyError):
                                pass
                    previous_values[key] = message
                self._dead = False
            except redis.exceptions.ConnectionError:
                self._dead = True
            except (AttributeError, ValueError) as e:
                _Logger().error(f"Something went wrong while processing hooks: {e!r}")
            if not self.running:
                break
            time.sleep(0.01)

    def connect(self) -> None:
        self.redis = redis.Redis(host=self._host, port=self._port, db=self._db, decode_responses=True)
        self.pubsub = self.redis.pubsub()
        self._start_hooks()
        try:
            self.redis.ping()
            self._dead = False
            if self.on_connect:
                self.on_connect()
        except redis.exceptions.ConnectionError as e:
            _Logger().error(f"Redis connection error: {e}")
            self._dead = True
            self.redis = None
            if self.on_disconnect:
                self.on_disconnect()
            return
        self._listener_thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="KevinbotLib.Redis.Listener"
        )
        self._listener_thread.start()

    def is_connected(self) -> bool:
        """Check if the Redis connection is established."""
        return self.redis is not None and self.redis.connection_pool is not None and not self._dead

    def get_latency(self) -> float | None:
        """Measure the round-trip latency to the Redis server in milliseconds."""
        if not self.redis:
            return None
        try:
            import time

            start_time = time.time()
            self.redis.config_get("maxclients")
            end_time = time.time()
            return (end_time - start_time) * 1000  # Convert to milliseconds
        except redis.exceptions.ConnectionError as e:
            _Logger().error(f"Cannot measure latency: {e}")
            self._dead = True
            return None

    def wait_until_connected(self, timeout: float = 5.0):
        """Wait until the Redis connection is established."""
        start_time = time.time()
        while not self.redis or not self.redis.ping():
            if time.time() > start_time + timeout:
                self._dead = True
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
        except redis.exceptions.ConnectionError:
            self._dead = True
            return

    def reset_connection(self):
        """Reset the connection to the Redis server"""
        if self.running:
            # get subs
            subscriptions = {}
            if self.pubsub:
                subscriptions = self.pubsub.channels

            self.close()

            self.redis = redis.Redis(host=self._host, port=self._port, db=self._db, decode_responses=True)
            self.pubsub = self.redis.pubsub()
            for sub in subscriptions.values():
                if sub is None:
                    continue
                try:
                    self.pubsub.subscribe(sub)
                except redis.exceptions.ConnectionError:
                    self._dead = True
                    _Logger().warning(f"Failed to re-subscribe to {sub}, client is not connected")

            self._start_hooks()

            self._listener_thread = threading.Thread(
                target=self._listen_loop, daemon=True, name="KevinbotLib.Redis.Listener"
            )
            self._listener_thread.start()

            checker = threading.Thread(target=self._redis_connection_check, daemon=True)
            checker.setName("KevinbotLib.Redis.ConnCheck")
            checker.start()

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @host.setter
    def host(self, value: str):
        self._host = value
        if self.redis:
            self.redis.connection_pool.connection_kwargs["host"] = value
        self.reset_connection()

    @port.setter
    def port(self, value: int):
        self._port = value
        if self.redis:
            self.redis.connection_pool.connection_kwargs["port"] = value
        self.reset_connection()
