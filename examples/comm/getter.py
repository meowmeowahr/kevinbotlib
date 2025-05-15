import time

from kevinbotlib.comm import IntegerSendable, RedisCommClient, StringSendable
from kevinbotlib.logger import Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration())

client = RedisCommClient()
client.connect()
client.wait_until_connected()

try:
    while True:
        print(client.get("example/hierarchy/test", IntegerSendable))
        print(client.get("example/hierarchy/test2", StringSendable))
        time.sleep(0.1)
except KeyboardInterrupt:
    client.close()
