import time
from kevinbotlib.scheduler import Command, CommandScheduler, ParallelCommand, SequentialCommand, Trigger


class PrintCommand(Command):
    def __init__(self, message: str):
        self.message = message
        self._finished = False
        self.iters = 0

    def init(self):
        print(f"Initializing: {self.message}")

    def execute(self):
        print(self.message)
        self.iters += 1
        if self.iters == 5:
            self._finished = True

    def end(self):
        print(f"Ending: {self.message}")

    def finished(self):
        return self._finished

start_time = time.time()

scheduler = CommandScheduler()

trigger = Trigger(lambda: True, scheduler)
trigger.while_true(SequentialCommand([PrintCommand("Command 1"), PrintCommand("Command 2"), PrintCommand("Command 3")]))

for _ in range(100):
    scheduler.iterate()
    time.sleep(0.1)