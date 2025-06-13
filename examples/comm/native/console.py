from kevinbotlib.logger import Logger, LoggerConfiguration
from kevinbotlib.comm.core.client import NetworkClientCore

if __name__ == '__main__':
    Logger().configure(LoggerConfiguration())

    client = NetworkClientCore("127.0.0.1", 8888)
    client.connect()

    while True:
        inp = input(">>> ")
        print(f"<<< {client.raw_send(inp)}")