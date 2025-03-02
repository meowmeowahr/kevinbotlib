import random
import time

from kevinbotlib.comm import BaseSendable, IntegerSendable, KevinbotCommClient, SendableGenerator
from kevinbotlib.logger import Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration())

client = KevinbotCommClient()
client.connect()
client.wait_until_connected()

class TestGenerator(SendableGenerator):
    def generate_sendable(self) -> BaseSendable:
        return IntegerSendable(value=random.randint(0, 100))

generator = TestGenerator()

try:
    while True:
        client.send("example/hierarchy/test", generator)
        time.sleep(0.5)
except KeyboardInterrupt:
    client.disconnect()
