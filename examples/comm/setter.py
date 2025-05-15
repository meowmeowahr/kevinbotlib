import time

from kevinbotlib.comm import IntegerSendable, RedisCommClient, StringSendable
from kevinbotlib.logger import Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration())

client = RedisCommClient()
client.connect()
client.wait_until_connected()

i = 0
try:
    while True:
        client.set("example/hierarchy/test", IntegerSendable(value=i))
        client.set("example/hierarchy/test2", StringSendable(value=f"demo {i}"))
        time.sleep(0.5)
        i += 1
except KeyboardInterrupt:
    client.close()
