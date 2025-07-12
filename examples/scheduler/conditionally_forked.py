from kevinbotlib.scheduler import Command, CommandScheduler, ConditionallyForkedCommand


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


if __name__ == "__main__":
    scheduler = CommandScheduler()
    scheduler.schedule(
        ConditionallyForkedCommand(lambda: True, PrintCommand("Condition Met"), PrintCommand("Condition Not Met"))
    )
    scheduler.schedule(
        ConditionallyForkedCommand(lambda: False, PrintCommand("Condition Met"), PrintCommand("Condition Not Met"))
    )

    for _ in range(2):
        scheduler.iterate()
