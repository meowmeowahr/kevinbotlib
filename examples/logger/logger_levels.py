from kevinbotlib.logger import Level, Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration(Level.TRACE))  # lowest available level

logger.trace("A trace message")
logger.debug("A debug message")
logger.info("An info message")
logger.warning("A warning message")
logger.error("An error message")
logger.security("A secutity warning or error")
logger.critical("A critical message")
