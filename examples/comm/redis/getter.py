import time

from kevinbotlib.comm.redis import RedisCommClient
from kevinbotlib.comm.request import GetRequest
from kevinbotlib.comm.sendables import IntegerSendable, StringSendable
from kevinbotlib.logger import Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration())

client = RedisCommClient()
client.connect()
client.wait_until_connected()

try:
    while True:
        # ! don't do this
        # print(client.get("example/hierarchy/test", IntegerSendable))
        # print(client.get("example/hierarchy/test2", StringSendable))
        test, test2 = client.multi_get(
            [
                GetRequest("example/hierarchy/test", IntegerSendable),
                GetRequest("example/hierarchy/test2", StringSendable),
            ]
        )
        print(test)
        print(test2)
        time.sleep(0.1)
except KeyboardInterrupt:
    client.close()
