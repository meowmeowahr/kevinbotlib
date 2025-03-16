import time

from kevinbotlib.comm import IntegerSendable, CommunicationClient, StringSendable
from kevinbotlib.logger import Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration())

client = CommunicationClient()
client.connect()
client.wait_until_connected()

i = 0
try:
    while True:
        client.send("example/hierarchy/test", IntegerSendable(value=i, timeout=None))
        client.send("example/hierarchy/tes2", StringSendable(value=f"demo {i}", timeout=None))
        time.sleep(0.5)
        i += 1
except KeyboardInterrupt:
    client.disconnect()
