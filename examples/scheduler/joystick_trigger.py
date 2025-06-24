import time

from kevinbotlib.joystick import LocalNamedController
from kevinbotlib.logger import Logger, LoggerConfiguration
from kevinbotlib.scheduler import Command, CommandScheduler

logger = Logger()
logger.configure(LoggerConfiguration())


class PrintCommand(Command):
    def __init__(self, message: str):
        self.message = message
        self._finished = False

    def init(self):
        print(f"Initializing: {self.message}")

    def execute(self):
        print(self.message)
        self._finished = True

    def end(self):
        print(f"Ending: {self.message}")

    def finished(self):
        return self._finished


class PrintForOneSecondCommand(Command):
    def __init__(self, message: str):
        self.message = message
        self._finished = False
        self.start = time.time()

    def init(self):
        self.start = time.time()
        print(f"Initializing: {self.message}")

    def execute(self):
        print(self.message)

    def end(self):
        print(f"Ending: {self.message}")

    def finished(self):
        return time.time() > self.start + 1


start_time = time.time()


scheduler = CommandScheduler()

controller = LocalNamedController(0)
controller.start_polling()

controller.command.a().while_true(PrintForOneSecondCommand("A Button Command"))
controller.command.b().on_true(PrintForOneSecondCommand("B Button Command"))
controller.command.x().on_true(PrintCommand("X Button Command"))

while True:
    scheduler.iterate()
    time.sleep(0.1)
