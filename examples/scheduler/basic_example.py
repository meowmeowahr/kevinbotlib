from kevinbotlib.scheduler import Command, CommandScheduler


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


scheduler = CommandScheduler()
scheduler.schedule(PrintCommand("Test"))
scheduler.schedule(PrintCommand("Test2"))
scheduler.iterate()
