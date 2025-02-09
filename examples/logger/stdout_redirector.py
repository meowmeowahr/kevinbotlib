import contextlib

from kevinbotlib.logger import Logger, StreamRedirector

logger = Logger()
stream = StreamRedirector(logger)

with contextlib.redirect_stdout(stream):
    print("Hello from KevinbotLib!")
    print("This will be converted to a logging entry")
