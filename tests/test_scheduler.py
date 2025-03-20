from kevinbotlib.scheduler import Command, CommandScheduler


def test_scheduler():
    class TestCommand(Command):
        def __init__(self, flag: int) -> None:
            super().__init__()
            self.flag = flag

        def init(self):
            super().init()
            self.flag += 1

        def execute(self) -> None:
            return super().execute()

        def end(self) -> None:
            return super().end()

        def finished(self) -> bool:
            return True

    scheduler = CommandScheduler()
    c = TestCommand(0)

    scheduler.schedule(c)
    scheduler.iterate()
    assert c.flag == 1

    scheduler.iterate()
    assert c.flag == 1

    scheduler.schedule(c)
    scheduler.iterate()
    assert c.flag == 2
