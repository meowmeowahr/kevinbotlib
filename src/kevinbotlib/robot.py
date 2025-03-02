import atexit
import contextlib
import os
import platform
import signal
import sys
import tempfile
import threading
import time
from threading import Thread
from types import TracebackType
from typing import NoReturn, final

import psutil

from kevinbotlib.comm import ControlConsoleSendable, KevinbotCommClient, KevinbotCommServer
from kevinbotlib.exceptions import RobotEmergencyStoppedException, RobotLockedException, RobotStoppedException
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


class InstanceLocker:
    def __init__(self, lockfile_name: str):
        """Initialize the InstanceLocker

        Args:
            lockfile_name (str): The name of the lockfile (e.g., 'robot.lock').
        """
        self.lockfile_name = lockfile_name
        self.pid = os.getpid()
        self._locked = False

    def lock(self) -> bool:
        """Attempt to acquire the lock by creating a lockfile with the current PID.

        Returns:
            bool: True if the lock was successfully acquired, False if another instance is running.
        """
        if self._locked:
            return True  # Already locked by this instance

        # Check if another instance is running
        if self.is_locked(self.lockfile_name):
            return False

        # Try to create the lockfile
        try:
            with open(os.path.join(tempfile.gettempdir(), self.lockfile_name), "w") as f:
                f.write(str(self.pid))
            self._locked = True
        except FileExistsError:
            # Double-check in case of race condition
            if self.is_locked(self.lockfile_name):
                return False
            # If the process is gone, overwrite the lockfile
            with open(os.path.join(tempfile.gettempdir(), self.lockfile_name), "w") as f:
                f.write(str(self.pid))
            self._locked = True
            return True
        except OSError as e:
            Logger().error(f"Failed to create lockfile: {e!r}")
            return False
        else:
            return True

    def unlock(self) -> None:
        """Release the lock by removing the lockfile."""
        if not self._locked:
            return

        try:
            if os.path.exists(os.path.join(tempfile.gettempdir(), self.lockfile_name)):
                with open(os.path.join(tempfile.gettempdir(), self.lockfile_name)) as f:
                    pid = f.read().strip()
                if pid == str(self.pid):  # Only remove if this process owns the lock
                    os.remove(os.path.join(tempfile.gettempdir(), self.lockfile_name))
            self._locked = False
        except OSError as e:
            Logger().error(f"Failed to remove lockfile: {e!r}")

    @staticmethod
    def is_locked(lockfile_name: str) -> int:
        """Check if the lockfile exists and corresponds to a running process.

        Args:
            lockfile_name (str): The name of the lockfile to check.

        Returns:
            int: -1 if not locked, PID of locking process
        """
        if not os.path.exists(os.path.join(tempfile.gettempdir(), lockfile_name)):
            return False

        try:
            with open(os.path.join(tempfile.gettempdir(), lockfile_name)) as f:
                pid_str = f.read().strip()
                pid = int(pid_str)
        except (OSError, ValueError):
            # If the file is corrupt or unreadable, assume it's stale and not locked
            return False
        return pid in [p.info["pid"] for p in psutil.process_iter(attrs=["pid", "name"])]

    def __enter__(self) -> "InstanceLocker":
        """Context manager support: acquire the lock."""
        self.lock()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager support: release the lock."""
        self.unlock()


class BaseRobot:
    def __init__(
        self,
        opmodes: list[str],
        serve_port: int = 8765,
        log_level: Level = Level.INFO,
        print_level: Level = Level.INFO,
        default_opmode: str | None = None,
        cycle_time: float = 250,
        log_cleanup_timer: float = 10.0
    ):
        """
        Initialize the robot

        Args:
            opmodes (list[str]): List of operational mode names.
            serve_port (int, optional): Port for comm server. Shouldn't have to be changed in most cases. Defaults to 8765.
            log_level (Level, optional): Level to logging. Defaults to Level.INFO.
            print_level (Level, optional): Level for print statement redirector. Defaults to Level.INFO.
            default_opmode (str, optional): Default Operational Mode to start in. Defaults to the first item of `opmodes`.
            cycle_time (float, optional): How fast to run periodic functions in Hz. Defaults to 250.
            log_cleanup_timer (float, optional): How often to cleanup logs in seconds Set to 0 to disable log cleanup. Defaults to 10.0.
        """

        self.telemetry = Logger()
        self.telemetry.configure(LoggerConfiguration(level=log_level, file_logger=FileLoggerConfig()))

        sys.excepthook = self._exc_hook
        threading.excepthook = self._thread_exc_hook

        self.fileserver = FileServer(LoggerDirectories.get_logger_directory())

        self._instance_locker = InstanceLocker(f"{self.__class__.__name__}.lock")
        atexit.register(self._instance_locker.unlock)

        self._opmodes = opmodes

        self.comm_server = KevinbotCommServer(port=serve_port)
        self.comm_client = KevinbotCommClient(port=serve_port)

        self._print_log_level = print_level
        self._log_timer_interval = log_cleanup_timer

        self._ctrl_sendable: ControlConsoleSendable = ControlConsoleSendable(
            opmode=default_opmode or opmodes[0], opmodes=opmodes
        )
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
    def _thread_exc_hook(self, args):
        self._exc_hook(*args)

    @final
    def _exc_hook(self, _: type, exc_value: BaseException, __: TracebackType, *_args):
        if isinstance(exc_value, RobotEmergencyStoppedException | RobotStoppedException):
            return
        self.telemetry.log(
            Level.CRITICAL, "The robot stopped due to an exception", LoggerWriteOpts(exception=exc_value)
        )

    @final
    def _log_cleanup_internal(self):
        LoggerDirectories.cleanup_logs(LoggerDirectories.get_logger_directory())
        self.telemetry.trace("Cleaned up logs")
        if self._log_timer_interval != 0:
            timer = threading.Timer(self._log_timer_interval, self._log_cleanup_internal)
            timer.setDaemon(True)
            timer.setName("KevinbotLib.Cleanup.LogCleanup")
            timer.start()
    @final
    def run(self) -> NoReturn:
        """Run the robot loop. Method is **final**."""
        if InstanceLocker.is_locked(f"{self.__class__.__name__}.lock"):
            msg = f"Another robot with the class name {self.__class__.__name__} is already running"
            raise RobotLockedException(msg)
        self._instance_locker.lock()

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

        self.fileserver.start()

        if self._log_timer_interval != 0:
            timer = threading.Timer(self._log_timer_interval, self._log_cleanup_internal)
            timer.setDaemon(True)
            timer.setName("KevinbotLib.Cleanup.LogCleanup")
            timer.start()

        with contextlib.redirect_stdout(StreamRedirector(self.telemetry, self._print_log_level)):
            self.comm_client.wait_until_connected()
            self.comm_client.send(self._ctrl_sendable_key, self._ctrl_sendable)
            try:
                self.robot_start()
                self._ready_for_periodic = True
                self.telemetry.log(Level.INFO, "Robot started")

                while True:
                    sendable: ControlConsoleSendable | None = self.comm_client.get(
                        self._ctrl_sendable_key, ControlConsoleSendable
                    )
                    if sendable:
                        self._ctrl_sendable: ControlConsoleSendable = sendable
                    else:
                        self._ctrl_sendable.enabled = False
                        self.comm_client.send(self._ctrl_sendable_key, self._ctrl_sendable)

                    if self._signal_stop:
                        msg = "Robot signal stopped"
                        raise RobotStoppedException(msg)
                    if self._signal_estop:
                        msg = "Robot signal e-stopped"
                        raise RobotEmergencyStoppedException(msg)

                    if self._ctrl_sendable.opmodes != self._opmodes:
                        self._ctrl_sendable.opmodes = self._opmodes
                        self.comm_client.send(self._ctrl_sendable_key, self._ctrl_sendable)

                    if self._ctrl_sendable.opmode not in self._opmodes:
                        self.telemetry.error(
                            f"Got incorrect OpMode: {self._ctrl_sendable.opmode} from {self._ctrl_sendable.opmodes}"
                        )
                        self._ctrl_sendable.opmode = self._opmodes[0]  # Fallback to default opmode
                        self._ctrl_sendable.enabled = False
                        self.comm_client.send(self._ctrl_sendable_key, self._ctrl_sendable)

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
