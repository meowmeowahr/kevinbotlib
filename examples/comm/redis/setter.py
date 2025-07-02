import time

from kevinbotlib.comm.redis import RedisCommClient
from kevinbotlib.comm.request import SetRequest
from kevinbotlib.comm.sendables import IntegerSendable, StringSendable
from kevinbotlib.logger import Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration())

client = RedisCommClient()
client.connect()
client.wait_until_connected()

i = 0
try:
    while True:
        # ! don't do this
        # client.set("example/hierarchy/test", IntegerSendable(value=i))
        # client.set("example/hierarchy/test2", StringSendable(value=f"demo {i}"))
        client.multi_set(
            [
                SetRequest("example/hierarchy/test", IntegerSendable(value=i)),
                SetRequest("example/hierarchy/test2", StringSendable(value=f"demo {i}")),
            ]
        )
        time.sleep(0.5)
        i += 1
except KeyboardInterrupt:
    client.close()
