import time

from kevinbotlib.comm import KevinbotCommClient, StringData

client = KevinbotCommClient()
client.connect()
client.wait_until_connected()

i = 0
try:
    while True:
        client.send("example/hierarchy", StringData(value=f"demo {i}", timeout=None))
        time.sleep(0.5)
        i += 1
except KeyboardInterrupt:
    client.disconnect()
