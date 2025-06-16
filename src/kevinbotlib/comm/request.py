from dataclasses import dataclass
from typing import Generic, TypeVar

from kevinbotlib.comm.path import CommPath
from kevinbotlib.comm.sendables import BaseSendable

GetRequestTypeVar = TypeVar("GetRequestTypeVar", bound=BaseSendable)
SetRequestTypeVar = TypeVar("SetRequestTypeVar", bound=BaseSendable)


@dataclass
class GetRequest(Generic[GetRequestTypeVar]):
    """Dataclass for a Comm Get Request"""

    key: CommPath | str
    """Key to retrieve"""
    data_type: type[GetRequestTypeVar]
    """Sendable type"""


@dataclass
class SetRequest(Generic[SetRequestTypeVar]):
    """Dataclass for a Comm Set Request"""

    key: CommPath | str
    """Key to set"""
    data: SetRequestTypeVar
    """Sendable to set"""
