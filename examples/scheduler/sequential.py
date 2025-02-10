import time

from kevinbotlib.scheduler import Command, CommandScheduler, SequentialCommand


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
scheduler.schedule(SequentialCommand([PrintForOneSecondCommand("command 1"), PrintForOneSecondCommand("command 2")]))

while True:
    scheduler.iterate()
    time.sleep(0.1)
