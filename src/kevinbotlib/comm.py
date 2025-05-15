import json
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, ClassVar, TypeVar

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
        except redis.exceptions.ConnectionError as e:
            _Logger().error(f"Cannot get {key}: {e}")
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
            return self.redis.keys("*")
        except redis.exceptions.ConnectionError as e:
            _Logger().error(f"Cannot get keys: {e}")
            return []

    def get_all(self) -> dict[str, BaseSendable] | None:
        """Retrieve all sendables in the database, deserialized."""
        if not self.redis:
            _Logger().error("Cannot get all: client is not started")
            return None
        keys = self.get_keys()
        result = {}
        try:
            for key in keys:
                sendable = self.get(key)
                result[key] = sendable
        except redis.exceptions.ConnectionError as e:
            _Logger().error(f"Error retrieving all sendables: {e}")
            return None
        return result

    def get_raw(self, key: CommPath | str) -> dict | None:
        """Retrieve the raw JSON for a key."""
        if not self.redis:
            _Logger().error("Cannot get raw: client is not started")
            return None
        try:
            raw = self.redis.get(str(key))
            return orjson.loads(raw) if raw else None
        except (redis.exceptions.ConnectionError, orjson.JSONDecodeError) as e:
            _Logger().error(f"Cannot get raw {key}: {e}")
            return None

    def send(self, key: CommPath | str, sendable: BaseSendable | SendableGenerator) -> None:
        """Set a sendable in the Redis database."""
        if not self.running or not self.redis:
            _Logger().error(f"Cannot publish to {key}: client is not started")
            return

        if isinstance(sendable, SendableGenerator):
            sendable = sendable.generate_sendable()

        data = sendable.get_dict()
        try:
            if sendable.timeout:
                self.redis.set(str(key), orjson.dumps(data), px=int(sendable.timeout * 1000))
            else:
                self.redis.set(str(key), orjson.dumps(data))
        except redis.exceptions.ConnectionError as e:
            _Logger().error(f"Cannot publish to {key}: {e}")

    def wipeall(self) -> None:
        """Delete all keys in the Redis database."""
        if not self.redis:
            _Logger().error("Cannot wipe all: client is not started")
            return
        try:
            self.redis.flushdb()
            self.redis.flushall()
        except redis.exceptions.ConnectionError as e:
            _Logger().error(f"Cannot wipe all: {e}")

    def delete(self, key: CommPath | str) -> None:
        """Delete a key from the Redis database."""
        if not self.redis:
            _Logger().error("Cannot delete: client is not started")
            return
        try:
            self.redis.delete(str(key))
        except redis.exceptions.ConnectionError as e:
            _Logger().error(f"Cannot delete {key}: {e}")

    def _start_hooks(self) -> None:
        if not self.running:
            self.running = True
            self.sub_thread = threading.Thread(target=self._run_hooks, daemon=True)
            self.sub_thread.start()

    def _run_hooks(self):
        """Run the pubsub listener in a separate thread."""
        previous_values = {}
        redis_connection_error = False
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
                redis_connection_error = False
            except redis.exceptions.ConnectionError as e:
                if not redis_connection_error:
                    _Logger().error(f"Redis connection error: {e}")
                    if self.on_disconnect:
                        self.on_disconnect()
                    redis_connection_error = True
            except (AttributeError, ValueError) as e:
                _Logger().error(f"Something went wrong while processing hooks: {e!r}")
            if not self.running:
                break
            time.sleep(0.01)

    def connect(self) -> None:
        self.redis = redis.Redis(host=self._host, port=self._port, db=self._db, decode_responses=True)
        self._start_hooks()
        try:
            self.redis.ping()
            if self.on_connect:
                self.on_connect()
        except redis.exceptions.ConnectionError as e:
            _Logger().error(f"Redis connection error: {e}")
            self.redis = None
            if self.on_disconnect:
                self.on_disconnect()
            return

    def is_connected(self) -> bool:
        """Check if the Redis connection is established."""
        return self.redis is not None and self.redis.connection_pool is not None

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
            return None

    def wait_until_connected(self, timeout: float = 5.0):
        """Wait until the Redis connection is established."""
        start_time = time.time()
        while not self.redis or not self.redis.ping():
            if time.time() > start_time + timeout:
                msg = "The connection timed out"
                raise kevinbotlib.exceptions.HandshakeTimeoutException(msg)
            time.sleep(0.02)

    def close(self):
        """Close the Redis connection and stop the pubsub thread."""
        self.running = False
        if self.redis:
            self.redis.close()
            self.redis = None
        if self.sub_thread:
            self.sub_thread.join()
        if self.on_disconnect:
            self.on_disconnect()

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
        if self.running:
            self.close()
            self.redis = redis.Redis(host=self._host, port=self._port, db=self._db, decode_responses=True)
            self._start_hooks()

    @port.setter
    def port(self, value: int):
        self._port = value
        if self.redis:
            self.redis.connection_pool.connection_kwargs["port"] = value
        if self.running:
            self.close()
            self.redis = redis.Redis(host=self._host, port=self._port, db=self._db, decode_responses=True)
            self._start_hooks()
