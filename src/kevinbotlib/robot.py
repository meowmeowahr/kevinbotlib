import contextlib
import os
import platform
import signal
import time
from threading import Thread
from typing import NoReturn, final

from kevinbotlib.comm import KevinbotCommClient, KevinbotCommServer, OperationalModeSendable
from kevinbotlib.exceptions import RobotEmergencyStoppedException, RobotStoppedException
from kevinbotlib.fileserver.fileserver import FileServer
from kevinbotlib.logger import FileLoggerConfig, Level, Logger, LoggerConfiguration, LoggerDirectories, StreamRedirector


class BaseRobot():
    def __init__(
        self,
        serve_port: int = 8765,
        log_level: Level = Level.INFO,
        print_level: Level = Level.INFO,
        default_opmode: str = "Teleoperated",
    ):
        """_summary_

        Args:
            serve_port (int, optional): Port for comm server. Shouldn't have to be changed in most cases. Defaults to 8765.
            log_level (Level, optional): Level to logging. Defaults to Level.INFO.
            print_level (Level, optional): Level for print statement redirector. Defaults to Level.INFO.
            default_opmode (str, optional): Default Operational Mode to start in. Defaults to Teleoperated
        """
        self.telemetry = Logger()
        self.telemetry.configure(LoggerConfiguration(level=log_level, file_logger=FileLoggerConfig()))

        # self.fileserver = FileServer(LoggerDirectories.get_logger_directory())
        # self.fileserver.start()

        self.comm_server = KevinbotCommServer(port=serve_port)
        self.comm_client = KevinbotCommClient(port=serve_port)

        self._print_log_level = print_level

        self.current_opmode = default_opmode

        self._signal_stop = False
        self._signal_estop = False

    @final
    def _signal_usr1_capture(self, sig, frame):
        self.telemetry.critical("Signal stop detected... Stopping now")
        self._signal_stop = True

    @final
    def _signal_usr2_capture(self, sig, frame):
        self.telemetry.critical("Signal EMERGENCY STOP detected... Stopping now")
        self._signal_estop = True

    @final
    def run(self) -> NoReturn:
        """Run the robot loop. Method is **final**."""

        # platform checks
        if platform.system() != 'Linux':
            self.telemetry.warning("Non-Linux OSes are not fully supported. Features such as signal shutdown may be broken")

        # shutdown signal
        signal.signal(signal.SIGUSR1, self._signal_usr1_capture)
        signal.signal(signal.SIGUSR2, self._signal_usr2_capture)
        self.telemetry.debug(f"{self.__class__.__name__}'s process id is {os.getpid()}")

        Thread(
            target=self.comm_server.serve, daemon=True, name=f"KevinbotLib.Robot.{self.__class__.__name__}.CommServer"
        ).start()
        self.comm_server.wait_until_serving()
        self.comm_client.connect()

        with contextlib.redirect_stdout(StreamRedirector(self.telemetry, self._print_log_level)):
            self.comm_client.wait_until_connected()  # wait until connection before publishing data
            self.comm_client.send("SysOp/opmode", OperationalModeSendable()) # TODO: set defaults
            try:
                self.robot_start()
                self.telemetry.log(Level.INFO, "Robot started")
                while True:
                    if self._signal_stop:
                        raise RobotStoppedException("Robot signal stopped")
                    if self._signal_estop:
                        raise RobotEmergencyStoppedException("Robot signal e-stopped")
                    time.sleep(1)
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
