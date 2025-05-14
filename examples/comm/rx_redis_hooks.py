import time

from kevinbotlib.comm import IntegerSendable, RedisCommClient
from kevinbotlib.logger import Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration())

client = RedisCommClient()
# client.connect()
# client.wait_until_connected()


def hook(message) -> None:
    print(message)


client.add_hook("example/hierarchy/test", IntegerSendable, hook)

try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    client.close()
