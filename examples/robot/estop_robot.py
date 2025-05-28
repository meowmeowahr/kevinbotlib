from kevinbotlib.logger import Level
from kevinbotlib.robot import BaseRobot


class DemoRobot(BaseRobot):
    def __init__(self):
        super().__init__(
            opmodes=[
                "TestOp1",
            ],  # robot's operational modes
            log_level=Level.TRACE,  # lowset logging level
            enable_stderr_logger=True,
            cycle_time=20,  # loop our robot code 20x per second - it is recommended to run much higher in practice
            metrics_publish_timer=0,  # the test robot doesn't use metrics - see the metrics_robot.py example for a metrics usage example
        )

        BaseRobot.register_estop_hook(lambda: print("E-STOP Hook 1"))  # usually used for hardware shutdowns
        BaseRobot.register_estop_hook(
            lambda: print("E-STOP Hook 2")
        )  # they will run in a thread - *MUST BE THREAD-SAFE*

    def robot_start(self) -> None:  # runs once as the robot starts
        super().robot_start()
        print(
            "Starting robot..."
        )  # print statements are redirected to the KevinbotLib logging system - please don't do this in production

        self.estop()

    def robot_periodic(self, opmode: str, enabled: bool) -> None:
        super().robot_periodic(opmode, enabled)

        print(f"OpMode {'enabled' if enabled else 'disabled'}... {opmode}")

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
