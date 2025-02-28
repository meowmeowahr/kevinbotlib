from threading import Thread
from typing import final

from kevinbotlib.comm import KevinbotCommClient, KevinbotCommServer, OperationalModeSendable
from kevinbotlib.logger import Level, Logger, LoggerConfiguration


class BaseRobot:
    def __init__(self, serve_port: int = 8765, log_level: Level = Level.INFO):
        """Create a new robot

        Args:
            serve_port (int, optional): Port for comm server. Shouldn't have to be changed in most cases. Defaults to 8765.
        """
        self.comm_server = KevinbotCommServer(port=serve_port)
        Thread(
            target=self.comm_server.serve, daemon=True, name=f"KevinbotLib.Robot.{self.__class__.__name__}.CommServer"
        ).start()

        self.comm_client = KevinbotCommClient(port=serve_port)
        self.comm_client.connect()

        self.telemetry = Logger()
        self.telemetry.configure(LoggerConfiguration(level=log_level))

    @final
    def run(self):
        """Run the robot. Method is **final**."""
        self.comm_client.wait_until_connected()  # wait until connection before publishing data
        self.comm_client.send("SysOp/opmode", OperationalModeSendable())
        try:
            while True:
                pass
        finally:
            self.robot_end()

    def robot_start(self) -> None:
        """Run after the robot is initialized"""

    def robot_end(self) -> None:
        """Runs before the robot is requested to stop via service or keyboard interrupt"""

    def opmode_enabled_init(self, opmode: str) -> None:
        """Runs once when the robot is enabled

        Args:
            opmode (str): The OpMode the robot was enabled in. Default opmodes are `"Teleoperated"` and `"Test"`
        """

    def opmode_enabled_periodic(self, opmode: str) -> None:
        """Loops when the robot is enabled

        Args:
            opmode (str): The OpMode the robot is currently in. Default opmodes are `"Teleoperated"` and `"Test"`
        """

    def opmode_disabled_init(self, opmode: str, *, interupted: bool) -> None:
        """Runs once when the robot is disabled

        Args:
            opmode (str): The OpMode the robot was disabled in. Default opmodes are `"Teleoperated"` and `"Test"`
        """

    def opmode_disabled_periodic(self, opmode: str) -> None:
        """Loops when the robot is disabled

        Args:
            opmode (str): The OpMode the robot is currently in. Default opmodes are `"Teleoperated"` and `"Test"`
        """
