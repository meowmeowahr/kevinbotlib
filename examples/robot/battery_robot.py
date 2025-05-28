import random

from kevinbotlib.logger import Level
from kevinbotlib.robot import BaseRobot


class DemoRobot(BaseRobot):
    def __init__(self):
        super().__init__(
            opmodes=[
                "TestBatteryRobot",
            ],  # robot's operational modes
            log_level=Level.TRACE,  # lowest logging level
            enable_stderr_logger=True,
            cycle_time=5,  # loop our robot code 5x per second - it is recommended to run much higher in practice
            metrics_publish_timer=5.0,  # how often to publish new system metrics to the control console
        )
        BaseRobot.add_basic_metrics(self, update_interval=2.0)
        BaseRobot.add_battery(self, 6, 22, lambda: random.randrange(5, 20))

    def robot_start(self) -> None:  # runs once as the robot starts
        super().robot_start()
        print(
            "Starting robot..."
        )  # print statements are redirected to the KevinbotLib logging system - please don't do this in production

    def robot_periodic(self, opmode: str, enabled: bool) -> None:
        super().robot_periodic(opmode, enabled)

    def opmode_init(self, opmode: str, enabled: bool) -> None:
        super().opmode_init(opmode, enabled)

        print(f"OpMode {'enabled' if enabled else 'disabled'} init... {opmode}")

    def opmode_exit(self, opmode: str, enabled: bool) -> None:
        super().opmode_exit(opmode, enabled)

        print(f"OpMode {'enabled' if enabled else 'disabled'} exit... {opmode}")

    def robot_end(self) -> None:  # runs as the robot propares to shutdown
        super().robot_end()
        print("Ending robot...")


if __name__ == "__main__":
    DemoRobot().run()
