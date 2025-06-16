from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import TypeAlias, TypeVar

from kevinbotlib.comm.path import CommPath
from kevinbotlib.comm.request import GetRequest, SetRequest
from kevinbotlib.comm.sendables import BaseSendable, SendableGenerator

Ts = TypeVar("Ts", bound=BaseSendable)


class AbstractSetGetNetworkClient(ABC):
    @abstractmethod
    def register_type(self, data_type: type[BaseSendable]) -> None: ...

    @abstractmethod
    def add_hook(self, key: CommPath | str, data_type: type[Ts], callback: Callable[[str, Ts | None], None]) -> None: ...

    @abstractmethod
    def get(self, key: CommPath | str, data_type: type[Ts]) -> Ts | None: ...

    @abstractmethod
    def multi_get(self, requests: Sequence[GetRequest[Ts]]) -> list[Ts | None]: ...

    @abstractmethod
    def get_keys(self) -> list[str]: ...

    @abstractmethod
    def get_raw(self, key: CommPath | str) -> dict | None: ...

    @abstractmethod
    def get_all_raw(self) -> dict[str, dict] | None: ...

    @abstractmethod
    def set(self, key: CommPath | str, sendable: BaseSendable | SendableGenerator) -> None: ...

    @abstractmethod
    def multi_set(self, requests: Sequence[SetRequest]) -> None: ...

    @abstractmethod
    def delete(self, key: CommPath | str) -> None: ...

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def is_connected(self) -> bool: ...

    @abstractmethod
    def wait_until_connected(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @property
    @abstractmethod
    def host(self) -> str: ...

    @property
    @abstractmethod
    def port(self) -> int: ...

    @host.setter
    @abstractmethod
    def host(self, value: str): ...

    @port.setter
    @abstractmethod
    def port(self, value: int): ...

    @property
    @abstractmethod
    def timeout(self): ...


class AbstractPubSubNetworkClient(ABC):
    @abstractmethod
    def register_type(self, data_type: type[BaseSendable]) -> None: ...

    @abstractmethod
    def subscribe(self, key: CommPath | str, data_type: type[Ts], callback: Callable[[str, Ts], None]) -> None: ...

    @abstractmethod
    def publish(self, key: CommPath | str, sendable: BaseSendable | SendableGenerator) -> None: ...

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def is_connected(self) -> bool: ...

    @abstractmethod
    def wait_until_connected(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @property
    @abstractmethod
    def host(self) -> str: ...

    @property
    @abstractmethod
    def port(self) -> int: ...

    @host.setter
    @abstractmethod
    def host(self, value: str): ...

    @port.setter
    @abstractmethod
    def port(self, value: int): ...

    @property
    @abstractmethod
    def timeout(self): ...


SetGetClientWithPubSub: TypeAlias = type(
    "SetGetClientWithPubSub", (AbstractSetGetNetworkClient, AbstractPubSubNetworkClient), {}
)
