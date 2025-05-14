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
        client.send("example/hierarchy/test", IntegerSendable(value=i))
        client.send("example/hierarchy/test2", StringSendable(value=f"demo {i}"))
        time.sleep(0.5)
        i += 1
except KeyboardInterrupt:
    client.close()
