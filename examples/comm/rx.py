import time

from kevinbotlib.comm import KevinbotCommClient, StringSendable
from kevinbotlib.logger import Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration())

client = KevinbotCommClient(on_update=None)
client.connect()
client.wait_until_connected()

try:
    while True:
        print(client.get("example/hierarchy", StringSendable))
        time.sleep(0.1)
except KeyboardInterrupt:
    client.disconnect()
