from dataclasses import dataclass
from typing import TypeVar, Generic, TypeVarTuple

from kevinbotlib.comm.path import CommPath
from kevinbotlib.comm.sendables import BaseSendable

RequestTypeVar = TypeVar('RequestTypeVar', bound=BaseSendable)

@dataclass
class GetRequest(Generic[RequestTypeVar]):
    """Dataclass for a Comm Get Request"""

    key: CommPath | str
    """Key to retrieve"""
    data_type: type[RequestTypeVar]
    """Sendable type"""