import time

from kevinbotlib.fileserver import FileServer
from kevinbotlib.logger import Logger, LoggerDirectories

print(f"Logging to {LoggerDirectories.get_logger_directory()}")

fileserver = FileServer("admin", "password", LoggerDirectories.get_logger_directory())
fileserver.start()

logger = Logger()
LoggerDirectories.cleanup_logs(LoggerDirectories.get_logger_directory())
logger.configure_file_logger(LoggerDirectories.get_logger_directory(), "350MB")

logger.trace("A trace message")
logger.debug("A debug message")
logger.info("An info message")
logger.warning("A warning message")
logger.error("An error message")
logger.critical("A critical message")

while True:
    time.sleep(1)  # keep the fileserver up
