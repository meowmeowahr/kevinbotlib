from kevinbotlib.logger import Level, Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration(Level.TRACE))  # lowest available level

with Logger.suppress():
    Logger().error("You shouldn't see this!")

Logger().error("You should see this!")
