import atexit
import contextlib
import os
import platform
import signal
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from threading import Thread
from types import TracebackType
from typing import Any, NoReturn, final

import psutil

from kevinbotlib.__about__ import __version__
from kevinbotlib.comm import (
    AnyListSendable,
    BooleanSendable,
    CommPath,
    DictSendable,
    FloatSendable,
    RedisCommClient,
    StringSendable,
)
from kevinbotlib.exceptions import (
    LoggerNotConfiguredException,
    RobotEmergencyStoppedException,
    RobotLockedException,
    RobotStoppedException,
)
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
from kevinbotlib.metrics import Metric, MetricType, SystemMetrics
from kevinbotlib.remotelog import ANSILogSender
from kevinbotlib.system import SystemPerformanceData


class InstanceLocker:
    """
    Generate and release a lockfile for an entire application. Useful when trying to prevent multiple instances of an app.

    Verifies if the application was killed without releasing the lockfile.
    """

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
            True if the lock was successfully acquired, False if another instance is running.
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
            -1 if not locked, PID of locking process
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
    estop_hooks: list[Callable[[], Any]] = []  # noqa: RUF012

    @staticmethod
    def add_basic_metrics(robot: "BaseRobot", update_interval: float = 2.0):
        robot.metrics.add("cpu.usage", Metric("CPU Usage", 0.0, MetricType.PercentageUsedType))
        robot.metrics.add("memory.usage", Metric("Memory Usage", 0.0, MetricType.PercentageUsedType))
        robot.metrics.add("disk.usage", Metric("Disk Usage", 0.0, MetricType.PercentageUsedType))
        robot.metrics.add("kevinbotlib.version", Metric("KevinbotLib Version", __version__, MetricType.RawType))

        def metrics_updater():
            while True:
                robot.metrics.update("cpu.usage", SystemPerformanceData.cpu().total_usage_percent)
                robot.metrics.update("memory.usage", SystemPerformanceData.memory().percent)
                robot.metrics.update("disk.usage", SystemPerformanceData.primary_disk().percent)
                time.sleep(update_interval)

        threading.Thread(target=metrics_updater, name="KevinbotLib.Robot.Metrics.Updater", daemon=True).start()
        robot.telemetry.trace("Started telemetry thread")

    @staticmethod
    def add_battery(robot: "BaseRobot", min_voltage: int, max_voltage: int, source: Callable[[], float]):
        robot._batteries.append((min_voltage, max_voltage, source))  # noqa: SLF001
        if not robot._batt_publish_thread.is_alive():  # noqa: SLF001
            robot._batt_publish_thread.start()  # noqa: SLF001

    @staticmethod
    def register_estop_hook(hook: Callable[[], Any]):
        BaseRobot.estop_hooks.append(hook)

    def __init__(
        self,
        opmodes: list[str],
        serve_port: int = 6379,
        log_level: Level = Level.INFO,
        print_level: Level = Level.INFO,
        default_opmode: str | None = None,
        cycle_time: float = 250,
        log_cleanup_timer: float = 10.0,
        metrics_publish_timer: float = 5.0,
        battery_publish_timer: float = 0.1,
        robot_heartbeat_interval: float = 1.0,
        robot_heartbeat_expiry: float = 2.5,
        *,
        enable_stderr_logger: bool = False,
        allow_enable_without_console: bool = False,
    ):
        """
        Initialize the robot

        Args:
            opmodes (list[str]): List of operational mode names.
            serve_port (int, optional): Port for comm server. Shouldn't have to be changed in most cases. Defaults to 8765.
            log_level (Level, optional): Level to logging. Defaults to Level.INFO.
            print_level (Level, optional): Level for print statement redirector. Defaults to Level.INFO.
            enable_stderr_logger (bool, optional): Enable logging to STDERR, may cause issues when using signal stop. Defaults to False.
            default_opmode (str, optional): Default Operational Mode to start in. Defaults to the first item of `opmodes`.
            cycle_time (float, optional): How fast to run periodic functions in Hz. Defaults to 250.
            log_cleanup_timer (float, optional): How often to clean up logs in seconds. Set to 0 to disable log cleanup. Defaults to 10.0.
            metrics_publish_timer (float, optional): How often to **publish** system metrics. This is separate from `BaseRobot.add_basic_metrics()` update_interval. Set to 0 to disable metrics publishing. Defaults to 5.0.
            battery_publish_timer (float, optional): How often to **publish** battery voltages.  Set to 0 to disable battery publishing. Defaults to 0.1.
            robot_heartbeat_interval (float, optional): How often to send a heartbeat to the control console. Defaults to 1.0.
            robot_heartbeat_expiry (float, optional): How long the robot heartbeat will stay valid. Must be longer than robot_heartbeat_interval. Defaults to 2.0.
            allow_enable_without_console (bool, optional): Allow the robot to be enabled without an active control console. Defaults to False.
        """

        self.telemetry = Logger()
        self.telemetry.configure(
            LoggerConfiguration(
                level=log_level, enable_stderr_logger=enable_stderr_logger, file_logger=FileLoggerConfig()
            )
        )

        sys.excepthook = self._exc_hook
        threading.excepthook = self._thread_exc_hook
        self.telemetry.trace("Configured exception hooks")

        self.fileserver = FileServer(LoggerDirectories.get_logger_directory(), host="0.0.0.0")  # noqa: S104
        self.telemetry.trace("Configured file server")

        self._instance_locker = InstanceLocker(f"{self.__class__.__name__}.lock")
        atexit.register(self._instance_locker.unlock)
        self.telemetry.trace("Configured instance locker")

        self._opmodes = opmodes

        self._ctrl_status_root_key = "%ControlConsole/status"
        self._ctrl_request_root_key = "%ControlConsole/request"
        self._ctrl_heartbeat_key = "%ControlConsole/heartbeat"
        self._ctrl_metrics_key = "%ControlConsole/metrics"
        self._ctrl_logs_key = "%ControlConsole/logs"
        self._ctrl_batteries_key = "%ControlConsole/batteries"
        self._robot_heartbeat_key = "%Robot/heartbeat"

        self.comm_client = RedisCommClient(port=serve_port)
        self.log_sender = ANSILogSender(self.telemetry, self.comm_client, self._ctrl_logs_key)

        self._print_log_level = print_level
        self._log_timer_interval = log_cleanup_timer
        self._metrics_timer_interval = metrics_publish_timer
        self._robot_heartbeat_interval = robot_heartbeat_interval
        self._robot_heartbeat_expiry = robot_heartbeat_expiry
        self._allow_enable_without_console = allow_enable_without_console

        self._signal_stop = False
        self._signal_estop = False

        self._ready_for_periodic = False
        self._cycle_hz = cycle_time

        # Track the previous state for opmode transitions
        self._prev_enabled = None
        self._prev_opmode = None
        self._estop = False
        self._current_enabled: bool = False

        self._opmode = opmodes[0] if default_opmode is None else default_opmode

        self._metrics = SystemMetrics()

        self._batteries: list[tuple[float, float, Callable[[], float]]] = []
        self._batt_publish_thread: Thread = Thread(
            target=self._update_batteries, daemon=True, name="KevinbotLib.Robot.Battery.Updater"
        )
        self._batt_publish_interval = battery_publish_timer

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

        self.comm_client.subscribe(
            CommPath(self._ctrl_request_root_key) / "enabled", BooleanSendable, self._on_console_enabled_request
        )

        self.comm_client.connect()
        self._comm_connection_check_thread = Thread(target=self._comm_connection_check, daemon=True)
        self._comm_connection_check_thread.start()

        self.fileserver.start()

        if self._log_timer_interval != 0:
            timer = threading.Timer(self._log_timer_interval, self._log_cleanup_internal)
            timer.daemon = True
            timer.name = "KevinbotLib.Cleanup.LogCleanup"
            timer.start()

        if self._metrics_timer_interval != 0:
            timer = threading.Timer(self._metrics_timer_interval, self._metrics_pub_internal)
            timer.daemon = True
            timer.name = "KevinbotLib.Robot.Metrics.Updater"
            timer.start()

        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat,
            name="KevinbotLib.Robot.Heartbeat",
            daemon=True,
        )

        self.comm_client.wait_until_connected()
        self.comm_client.wipeall()
        self.log_sender.start()
        self._update_console_enabled(False)
        self._update_console_opmodes(self._opmodes)
        self._update_console_opmode(self._opmode)

    @property
    def metrics(self):
        return self._metrics

    @final
    def _heartbeat(self):
        if self._robot_heartbeat_expiry <= self._robot_heartbeat_interval:
            self.telemetry.error("robot_heartbeat_expiry must be longer than robot_heartbeat_interval")

        while True:
            if self._estop:
                self.telemetry.log(
                    Level.CRITICAL,
                    "Heartbeat stopped due to e-stop",
                    LoggerWriteOpts(exception=RobotEmergencyStoppedException()),
                )
                break
            self.comm_client.set(
                self._robot_heartbeat_key,
                FloatSendable(value=time.process_time(), timeout=self._robot_heartbeat_expiry),
            )
            time.sleep(self._robot_heartbeat_interval)

    @final
    def _comm_connection_check(self):
        while True:
            if not self.comm_client.is_connected():
                self.comm_client.connect()
            time.sleep(2)

    @final
    def _update_batteries(self):
        while True:
            self.comm_client.publish(
                self._ctrl_batteries_key,
                AnyListSendable(value=[(batt[0], batt[1], batt[2]()) for batt in self._batteries]),
            )
            time.sleep(self._batt_publish_interval)

    @final
    def _signal_usr1_capture(self, _, __):
        with contextlib.suppress(LoggerNotConfiguredException):
            self.telemetry.critical("Signal stop detected... Stopping now")
        self._signal_stop = True

    @final
    def _signal_usr2_capture(self, _, __):
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
            Level.CRITICAL,
            "The robot stopped due to an exception",
            LoggerWriteOpts(exception=exc_value),
        )

    @final
    def _log_cleanup_internal(self):
        LoggerDirectories.cleanup_logs(LoggerDirectories.get_logger_directory())
        self.telemetry.trace("Cleaned up logs")
        if self._log_timer_interval != 0:
            timer = threading.Timer(self._log_timer_interval, self._log_cleanup_internal)
            timer.daemon = True
            timer.name = "KevinbotLib.Cleanup.LogCleanup"
            timer.start()

    @final
    def _metrics_pub_internal(self):
        if self._metrics.getall():
            self.comm_client.set(
                CommPath(self._ctrl_metrics_key) / "metrics", DictSendable(value=self._metrics.getall())
            )
            self.telemetry.trace(f"Published system metrics to {self._ctrl_metrics_key}")
        else:
            self.telemetry.warning(
                "There were no metrics to publish, consider disabling metrics publishing to improve system resource usage"
            )

        if self._log_timer_interval != 0:
            timer = threading.Timer(self._metrics_timer_interval, self._metrics_pub_internal)
            timer.daemon = True
            timer.name = "KevinbotLib.Robot.Metrics.Publish"
            timer.start()

    @final
    def _update_console_enabled(self, enabled: bool):
        return self.comm_client.set(
            CommPath(self._ctrl_status_root_key) / "enabled",
            BooleanSendable(value=enabled),
        )

    @final
    def _update_console_opmodes(self, opmodes: list[str]):
        return self.comm_client.set(
            CommPath(self._ctrl_status_root_key) / "opmodes",
            AnyListSendable(value=opmodes),
        )

    @final
    def _update_console_opmode(self, opmode: str):
        return self.comm_client.set(
            CommPath(self._ctrl_status_root_key) / "opmode",
            StringSendable(value=opmode),
        )

    @final
    def _on_console_enabled_request(self, _: str, sendable: BooleanSendable | None):
        self._current_enabled = sendable.value if sendable else False

    @final
    def _get_console_opmode_request(self):
        sendable = self.comm_client.get(CommPath(self._ctrl_request_root_key) / "opmode", StringSendable)
        return sendable.value if sendable else self._opmodes[0]

    @final
    def _get_estop_request(self):
        return self.comm_client.get_raw(CommPath(self._ctrl_request_root_key) / "estop") is not None

    @final
    def _get_console_heartbeat_present(self):
        return self.comm_client.get_raw(CommPath(self._ctrl_heartbeat_key) / "heartbeat") is not None

    @final
    def run(self) -> NoReturn:
        """Run the robot loop. Method is **final**."""
        with contextlib.redirect_stdout(StreamRedirector(self.telemetry, self._print_log_level)):
            try:
                self._heartbeat_thread.start()
                self.telemetry.trace("Started heartbeat thread")
                self.robot_start()
                self._ready_for_periodic = True
                self.telemetry.log(Level.INFO, "Robot started")

                while True:
                    if self._signal_stop:
                        msg = "Robot signal stopped"
                        self.robot_end()
                        raise RobotStoppedException(msg)  # noqa: TRY301
                    if self._signal_estop:
                        msg = "Robot signal e-stopped"
                        raise RobotEmergencyStoppedException(msg)  # noqa: TRY301

                    if self._get_estop_request():
                        self.telemetry.critical("Control Console EMERGENCY STOP detected... Stopping now")
                        msg = "Robot control console e-stopped"
                        self._estop = True
                        raise RobotEmergencyStoppedException(msg)  # noqa: TRY301

                    current_opmode: str = self._get_console_opmode_request()

                    if not self._get_console_heartbeat_present() and not self._allow_enable_without_console:
                        if self._current_enabled:
                            self.telemetry.warning("Robot disabled due to CC timeout")
                        self._current_enabled = False

                    if self._ready_for_periodic:
                        # Handle opmode change
                        if current_opmode != self._opmode:
                            if self._prev_enabled is not None:  # Not first iteration
                                self.opmode_exit(self._opmode, self._prev_enabled)
                            self._opmode = current_opmode
                            self._update_console_opmode(current_opmode)
                            self.opmode_init(current_opmode, self._current_enabled)
                            self._prev_opmode = current_opmode

                        # Handle enable/disable transitions
                        if self._prev_enabled != self._current_enabled:
                            self._update_console_enabled(self._current_enabled)
                            self._prev_enabled = self._current_enabled

                        self.robot_periodic(self._opmode, self._current_enabled)

                    time.sleep(1 / self._cycle_hz)
            except RobotStoppedException:
                sys.exit(64)
            except RobotEmergencyStoppedException:
                self.telemetry.critical("Running E-Stop hooks...")
                stop_threads: list[Thread] = []
                for hook in BaseRobot.estop_hooks:
                    t = Thread(target=hook, name="KevinbotLib.Robot.EstopAction")
                    t.start()
                    stop_threads.append(t)

                for t in stop_threads:
                    t.join()

                time.sleep(1)
                self.comm_client.close()
                sys.exit(65)

    def robot_start(self) -> None:
        """Run after the robot is initialized"""

    def robot_end(self) -> None:
        """Runs before the robot is requested to stop via service or keyboard interrupt"""

    def robot_periodic(self, opmode: str, enabled: bool):
        """Periodically runs every robot cycle

        Args:
            opmode (str): The current OpMode
            enabled (bool): WHether the robot is enabled in this opmode
        """

    def opmode_init(self, opmode: str, enabled: bool) -> None:
        """Runs when entering an opmode state (either enabled or disabled)

        Args:
            opmode (str): The OpMode being entered
            enabled (bool): Whether the robot is enabled in this opmode
        """

    def opmode_exit(self, opmode: str, enabled: bool) -> None:
        """Runs when exiting an opmode state (either enabled or disabled)

        Args:
            opmode (str): The OpMode being exited
            enabled (bool): Whether the robot was enabled in this opmode
        """

    @property
    def enabled(self) -> bool:
        return self._prev_enabled if self._prev_enabled is not None else False

    @enabled.setter
    def enabled(self, value: bool):
        if not self._allow_enable_without_console and not self._get_console_heartbeat_present():
            self.telemetry.warning("Tried to dynamically enable without a connected control console")
            return
        self._update_console_enabled(value)
        self._current_enabled = value

    @property
    def opmode(self) -> str:
        return self._opmode

    @opmode.setter
    def opmode(self, value: str):
        if value not in self._opmodes:
            msg = f"Opmode '{value}' is not in allowed opmodes: {self._opmodes}"
            raise ValueError(msg)
        self._opmode = value
        self._update_console_opmode(value)

    @property
    def opmodes(self) -> list[str]:
        return self._opmodes

    def estop(self) -> None:
        """Immediately trigger an emergency stop."""
        self.telemetry.critical("Manual estop() called - triggering emergency stop")
        self._signal_estop = True
