from collections.abc import Sequence

from kevinbotlib.comm.abstract import AbstractSetGetNetworkClient
from kevinbotlib.comm.path import CommPath
from kevinbotlib.comm.request import SetRequest
from kevinbotlib.comm.sendables import BaseSendable


class PipelinedCommSetter:
    """
    Pipeline creator for optimized comm setting.
    Normally, a single set request may take as long as many pipelined requests, due to overhead.
    Using pipelines greatly optimizes robot cycle times.
    """

    def __init__(self, client: AbstractSetGetNetworkClient):
        """
        Create a new comm setter pipeline.

        Args:
            client: Client to use for the pipeline.
        """

        self.client = client
        self.set_queue: list[SetRequest] = []

    def add(self, request: SetRequest) -> None:
        """
        Add a new set request to the pipeline.

        Args:
            request: Set Request
        """
        self.set_queue.append(request)

    def set(self, key: CommPath | str, sendable: BaseSendable) -> None:
        """
        Add a new sendable to the pipeline.

        Args:
            key: Key to set
            sendable: Sendable to set
        """
        self.add(SetRequest(key, sendable))

    def extend(self, requests: Sequence[SetRequest]) -> None:
        """
        Adds a sequence of set requests to the pipeline.

        Args:
            requests: Set requests

        """
        self.set_queue.extend(requests)

    def send(self) -> None:
        """
        Apply the pipeline to the network client.
        """
        self.client.multi_set(self.set_queue)
        self.set_queue.clear()
