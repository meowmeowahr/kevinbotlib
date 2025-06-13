from kevinbotlib.comm.core.server import NetworkServer
from kevinbotlib.logger import Logger, LoggerConfiguration

if __name__ == "__main__":
    Logger().configure(LoggerConfiguration())

    server = NetworkServer("127.0.0.1", 8888)
    server.run()
