import contextlib

from kevinbotlib.logger import Level, Logger, LoggerConfiguration, StreamRedirector

logger = Logger()
logger.configure(LoggerConfiguration(Level.DEBUG))
stream = StreamRedirector(logger)

with contextlib.redirect_stdout(stream):
    print("Hello from KevinbotLib!")
    print("This will be converted to a logging entry")
