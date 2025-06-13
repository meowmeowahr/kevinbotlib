import random
import time

from kevinbotlib.comm.redis import (
    RedisCommClient,
)
from kevinbotlib.comm.sendables import (
    BaseSendable,
    IntegerSendable,
    SendableGenerator,
)
from kevinbotlib.logger import Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration())

client = RedisCommClient()
client.connect()
client.wait_until_connected()


class TestGenerator(SendableGenerator):
    def generate_sendable(self) -> BaseSendable:
        return IntegerSendable(value=random.randint(0, 100))


generator = TestGenerator()

try:
    while True:
        client.set("example/hierarchy/test", generator)
        time.sleep(0.5)
except KeyboardInterrupt:
    client.close()
