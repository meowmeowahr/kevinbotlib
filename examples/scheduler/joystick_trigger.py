import time

from kevinbotlib.joystick import LocalNamedController, NamedControllerButtons
from kevinbotlib.logger import Logger, LoggerConfiguration
from kevinbotlib.scheduler import Command, CommandScheduler, Trigger

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

Trigger(lambda: NamedControllerButtons.A in controller.get_buttons(), scheduler).while_true(
    PrintForOneSecondCommand("A Button Command")
)
Trigger(lambda: NamedControllerButtons.B in controller.get_buttons(), scheduler).on_true(
    PrintForOneSecondCommand("B Button Command")
)
Trigger(lambda: NamedControllerButtons.X in controller.get_buttons(), scheduler).on_true(
    PrintCommand("X Button Command")
)

while True:
    scheduler.iterate()
    time.sleep(0.1)
