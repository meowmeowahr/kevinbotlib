from kevinbotlib.logger import Logger, Level, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration(Level.DATA)) # lowest available level

logger.log(Level.DATA, "A data message")
logger.trace("A trace message")
logger.log(Level.HIGHFREQ, "A high frequency message")
logger.debug("A debug message")
logger.info("An info message")
logger.warning("A warning message")
logger.error("An error message")
logger.critical("A critical message")
