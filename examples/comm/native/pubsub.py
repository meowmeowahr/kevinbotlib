import time

from kevinbotlib.comm.core.client import NetworkClientCore
from kevinbotlib.logger import Logger, LoggerConfiguration

if __name__ == "__main__":
    Logger().configure(LoggerConfiguration())

    client = NetworkClientCore("127.0.0.1", 8888)
    client.connect()

    def on_recv(channel, message):
        print(f"Received message on channel {channel}: {message}")

    client.subscribe("example/pubsub", on_recv)

    client.pub("example/pubsub", "Hello, world!")

    while True:
        time.sleep(1)
