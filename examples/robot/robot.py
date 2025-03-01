from kevinbotlib.logger import Level
from kevinbotlib.robot import BaseRobot


class DemoRobot(BaseRobot):
    def robot_start(self) -> None:  # runs once as the robot starts
        super().robot_start()
        print(
            "Starting robot..."
        )  # print statements are redirected to the KevinbotLib logging system - please don't do this in production

    def robot_end(self) -> None:  # runs as the robot propares to shutdown
        super().robot_end()
        print("Ending robot...")


if __name__ == "__main__":
    DemoRobot(log_level=Level.TRACE).run() # run the robot with TRACE (lowest level) logging - recommended to use INFO or higher for production
