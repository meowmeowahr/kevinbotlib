from kevinbotlib.comm import (
    AnyListSendable,
    BooleanSendable,
    FloatSendable,
    IntegerSendable,
    StringSendable,
)
from kevinbotlib.logger import Level
from kevinbotlib.robot import BaseRobot


class DemoRobot(BaseRobot):
    def __init__(self):
        super().__init__(
            opmodes=[
                "TestOp1",
                "TestOp2",
                "TestOp3",
                "TestOp4",
            ],  # robot's operational modes
            log_level=Level.TRACE,  # lowset logging level
            enable_stderr_logger=True,
            cycle_time=20,  # loop our robot code 20x per second - it is recommended to run much higher in practice
            metrics_publish_timer=0,  # the test robot doesn't use metrics - see the metrics_robot.py example for a metrics usage example
        )

    def robot_start(self) -> None:  # runs once as the robot starts
        super().robot_start()
        print(
            "Starting robot..."
        )  # print statements are redirected to the KevinbotLib logging system - please don't do this in production

        self.comm_client.set("example/string", StringSendable(value="Hello World!"))
        self.comm_client.set("example/integer", IntegerSendable(value=1234))
        self.comm_client.set("example/float", FloatSendable(value=1234.56))
        self.comm_client.set("example/list", AnyListSendable(value=[1, 2, 3, 4]))
        self.comm_client.set("example/boolean", BooleanSendable(value=True))


if __name__ == "__main__":
    DemoRobot().run()
