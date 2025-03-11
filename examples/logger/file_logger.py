import time

from kevinbotlib.fileserver import FileServer
from kevinbotlib.logger import (
    FileLoggerConfig,
    Level,
    Logger,
    LoggerConfiguration,
    LoggerDirectories,
)

print(f"Logging to {LoggerDirectories.get_logger_directory()}")

logger = Logger()
logger.configure(LoggerConfiguration(Level.DEBUG, FileLoggerConfig()))

fileserver = FileServer(LoggerDirectories.get_logger_directory())
fileserver.start()

LoggerDirectories.cleanup_logs(LoggerDirectories.get_logger_directory())

logger.trace("A trace message")
logger.debug("A debug message")
logger.info("An info message")
logger.warning("A warning message")
logger.error("An error message")
logger.critical("A critical message")

while True:
    time.sleep(1)  # keep the fileserver up
