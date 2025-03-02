from kevinbotlib.logger import Level
from kevinbotlib.robot import BaseRobot


class DemoRobot(BaseRobot):
    def __init__(self):
        super().__init__(
            opmodes=["TestOp1", "TestOp2", "TestOp3", "TestOp4"], # robot's operational modes
            log_level=Level.TRACE, # lowset logging level
            cycle_time=20,  # loop our robot code 20x per second - it is recommended to run much higher in practice
        )

    def robot_start(self) -> None:  # runs once as the robot starts
        super().robot_start()
        print(
            "Starting robot..."
        )  # print statements are redirected to the KevinbotLib logging system - please don't do this in production

    def opmode_disabled_periodic(self, opmode: str) -> None:
        super().opmode_disabled_periodic(opmode)

        print(f"OpMode disabled... {opmode}")

    def opmode_enabled_periodic(self, opmode: str) -> None:
        super().opmode_enabled_periodic(opmode)

        print(f"OpMode enabled... {opmode}")

    def opmode_disabled_init(self, opmode: str) -> None:
        super().opmode_disabled_init(opmode)

        print(f"OpMode disabled init... {opmode}")

    def opmode_enabled_init(self, opmode: str) -> None:
        super().opmode_enabled_init(opmode)

        print(f"OpMode enabled init... {opmode}")

    def robot_end(self) -> None:  # runs as the robot propares to shutdown
        super().robot_end()
        print("Ending robot...")


if __name__ == "__main__":
    DemoRobot().run()
