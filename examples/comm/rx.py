import time

from kevinbotlib.comm import IntegerSendable, CommunicationClient, StringSendable
from kevinbotlib.logger import Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration())

client = CommunicationClient(on_update=None)
client.connect()
client.wait_until_connected()

try:
    while True:
        print(client.get("example/hierarchy/test", IntegerSendable))
        print(client.get("example/hierarchy/test2", StringSendable))
        time.sleep(0.1)
except KeyboardInterrupt:
    client.disconnect()
