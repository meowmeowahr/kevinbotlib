from kevinbotlib.comm import KevinbotCommServer
from kevinbotlib.logger import Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration())

server = KevinbotCommServer()
server.serve()
