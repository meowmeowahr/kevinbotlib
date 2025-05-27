import time

from kevinbotlib.fileserver import FileServer
from kevinbotlib.logger import Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration())

server = FileServer(
    http_port=8000,  # http
    directory="./",  # serve directory
)

try:
    server.start()

    while True:
        time.sleep(1)
except KeyboardInterrupt:
    server.stop()
