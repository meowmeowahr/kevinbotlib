import time

from kevinbotlib.comm import KevinbotCommClient, StringData

client = KevinbotCommClient(on_update=None)
client.connect()
client.wait_until_connected()

try:
    while True:
        print(client.get("streams/camera0/frame", StringData))  # noqa: T201
        time.sleep(0.1)
except KeyboardInterrupt:
    client.disconnect()
