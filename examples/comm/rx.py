import time

from kevinbotlib.comm import KevinbotCommClient, StringData

client = KevinbotCommClient(on_update=None)
client.connect()
client.wait_until_connected()

try:
    while True:
        print(client.get("example/hierarchy", StringData))
        time.sleep(0.1)
except KeyboardInterrupt:
    client.disconnect()
