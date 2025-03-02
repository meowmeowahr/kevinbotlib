import contextlib
import os
import platform
import signal
import sys
import time
from threading import Thread
from typing import NoReturn, final

from kevinbotlib.comm import ControlConsoleSendable, KevinbotCommClient, KevinbotCommServer
from kevinbotlib.exceptions import RobotEmergencyStoppedException, RobotStoppedException
from kevinbotlib.fileserver.fileserver import FileServer
from kevinbotlib.logger import (
    FileLoggerConfig,
    Level,
    Logger,
    LoggerConfiguration,
    LoggerDirectories,
    LoggerWriteOpts,
    StreamRedirector,
)


class BaseRobot:
    def __init__(
        self,
        opmodes: list[str],
        serve_port: int = 8765,
        log_level: Level = Level.INFO,
        print_level: Level = Level.INFO,
        default_opmode: str | None = None,
        cycle_time: float = 250,
    ):
        """_summary_

        Args:
            opmodes (list[str]): List of operational mode names.
            serve_port (int, optional): Port for comm server. Shouldn't have to be changed in most cases. Defaults to 8765.
            log_level (Level, optional): Level to logging. Defaults to Level.INFO.
            print_level (Level, optional): Level for print statement redirector. Defaults to Level.INFO.
            default_opmode (str, optional): Default Operational Mode to start in. Defaults to Teleoperated
            cycle_time (float, optional): How fast to run periodic functions in Hz. Defaults to 250.
        """
        self.telemetry = Logger()
        self.telemetry.configure(LoggerConfiguration(level=log_level, file_logger=FileLoggerConfig()))

        self.fileserver = FileServer(LoggerDirectories.get_logger_directory())
        self.fileserver.start()

        self._opmodes = opmodes

        self.comm_server = KevinbotCommServer(port=serve_port)
        self.comm_client = KevinbotCommClient(port=serve_port)

        self._print_log_level = print_level

        self._ctrl_sendable: ControlConsoleSendable = ControlConsoleSendable(opmode=default_opmode or opmodes[0], opmodes=opmodes)
        self._ctrl_sendable_key = "%ControlConsole"

        self._signal_stop = False
        self._signal_estop = False

        self._ready_for_periodic = False
        self._cycle_hz = cycle_time

        # Track the previous state for opmode transitions
        self._prev_enabled = None  # Was the robot previously enabled?

    @final
    def _signal_usr1_capture(self, _, __):
        self.telemetry.critical("Signal stop detected... Stopping now")
        self._signal_stop = True

    @final
    def _signal_usr2_capture(self, _, __):
        """Internal method used for the *EMERGENCY STOP* system **DO NOT OVERRIDE**"""
        self.telemetry.critical("Signal EMERGENCY STOP detected... Stopping now")
        self._signal_estop = True

    @final
    def run(self) -> NoReturn:
        """Run the robot loop. Method is **final**."""
        try:
            if platform.system() != "Linux":
                self.telemetry.warning(
                    "Non-Linux OSes are not fully supported. Features such as signal shutdown may be broken"
                )

            signal.signal(signal.SIGUSR1, self._signal_usr1_capture)
            signal.signal(signal.SIGUSR2, self._signal_usr2_capture)
            self.telemetry.debug(f"{self.__class__.__name__}'s process id is {os.getpid()}")

            Thread(
                target=self.comm_server.serve,
                daemon=True,
                name=f"KevinbotLib.Robot.{self.__class__.__name__}.CommServer",
            ).start()
            self.comm_server.wait_until_serving()
            self.comm_client.connect()

            with contextlib.redirect_stdout(StreamRedirector(self.telemetry, self._print_log_level)):
                self.comm_client.wait_until_connected()
                self.comm_client.send(self._ctrl_sendable_key, self._ctrl_sendable)
                try:
                    self.robot_start()
                    self._ready_for_periodic = True
                    self.telemetry.log(Level.INFO, "Robot started")

                    while True:
                        sendable: ControlConsoleSendable | None = self.comm_client.get(self._ctrl_sendable_key, ControlConsoleSendable)
                        if sendable:
                            self._ctrl_sendable: ControlConsoleSendable = sendable
                        else:
                            self._ctrl_sendable = self._ctrl_sendable.disabled()
                            self.comm_client.send(self._ctrl_sendable_key, self._ctrl_sendable)

                        if self._signal_stop:
                            msg = "Robot signal stopped"
                            raise RobotStoppedException(msg)
                        if self._signal_estop:
                            msg = "Robot signal e-stopped"
                            raise RobotEmergencyStoppedException(msg)

                        if self._ctrl_sendable.opmode not in self._ctrl_sendable.opmodes:
                            self.telemetry.error(
                                f"Got incorrect OpMode: {self._ctrl_sendable.opmode} from {self._ctrl_sendable.opmodes}"
                            )
                            self._ctrl_sendable.opmode = self._opmodes[0]  # Fallback to default opmode

                        if self._ready_for_periodic:
                            current_enabled: bool = self._ctrl_sendable.enabled
                            if self._ctrl_sendable:
                                current_opmode = self._ctrl_sendable.opmode

                            if self._prev_enabled != current_enabled:
                                if current_enabled:
                                    self.opmode_enabled_init(current_opmode)
                                else:
                                    self.opmode_disabled_init(current_opmode)

                            if current_enabled:
                                self.opmode_enabled_periodic(current_opmode)
                            else:
                                self.opmode_disabled_periodic(current_opmode)

                            self._prev_enabled = current_enabled
                            self._prev_opmode = current_opmode

                        time.sleep(1 / self._cycle_hz)
                finally:
                    self.robot_end()
        except Exception:  # noqa: BLE001
            self.telemetry.log(
                Level.CRITICAL, "Robot code execution stopped due to an exception", LoggerWriteOpts(exception=True)
            )
            sys.exit(1)

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

    def opmode_disabled_init(self, opmode: str) -> None:
        """Runs once when the robot is disabled

        Args:
            opmode (str): The OpMode the robot was disabled in. Default opmodes are `"Teleoperated"` and `"Test"`
        """

    def opmode_disabled_periodic(self, opmode: str) -> None:
        """Loops when the robot is disabled

        Args:
            opmode (str): The OpMode the robot is currently in. Default opmodes are `"Teleoperated"` and `"Test"`
        """
