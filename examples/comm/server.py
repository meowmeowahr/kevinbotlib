from kevinbotlib.comm import CommunicationServer
from kevinbotlib.logger import Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration())

server = CommunicationServer()
server.serve()
