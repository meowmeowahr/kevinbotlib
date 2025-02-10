import time
from kevinbotlib.scheduler import Command, CommandScheduler, Trigger


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

start_time = time.time()


scheduler = CommandScheduler()

trigger = Trigger(lambda: start_time < time.time() - 1, scheduler)
trigger.on_true(PrintCommand("Test"))

while True:
    scheduler.iterate()
    time.sleep(0.02)