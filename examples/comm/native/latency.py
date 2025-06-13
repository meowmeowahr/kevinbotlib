import time

from kevinbotlib.comm.core.client import NetworkClientCore
from kevinbotlib.logger import Logger, LoggerConfiguration

if __name__ == "__main__":
    Logger().configure(LoggerConfiguration())

    client = NetworkClientCore("127.0.0.1", 8888)
    client.connect()

    while True:
        print(f"{client.get_latency()}ms")
        time.sleep(1)
