import uuid

from kevinbotlib.__about__ import __version__
from kevinbotlib.logger import Logger as _Logger

VERSION = __version__

class Kevinbot:
    def __init__(self, host: str = "localhost", port: int = 1883, client_id: str | None = None) -> None:
        self.host = host
        self.port = port
        self.client_id = client_id if client_id else f"kevinbotlib-{uuid.uuid4()}"
        self.logger = _Logger()
        self.logger.debug(f"New KevinbotLib {VERSION} robot client created with id: {self.client_id}")
