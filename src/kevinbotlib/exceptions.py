class HandshakeTimeoutException(BaseException):
    """Exception that is produced when the server-up wait times out"""


class JoystickMissingException(BaseException):
    """Exception that is produced when a requested gamepad is missing"""


class CommandSchedulerAlreadyExistsException(BaseException):
    """Exception that is produced when an attempt to create more than one command scheduler was made"""


class CommandSchedulerDoesNotExistException(BaseException):
    """Exception that is produced when an attempt to get the current scheduler instance before creating a CommandScheduler"""


class LoggerNotConfiguredException(BaseException):
    """Exception that is produced when trying to log to a non-configured logger"""


class RobotStoppedException(BaseException):
    """Used when a non-urgent robot stop is triggered"""


class RobotEmergencyStoppedException(BaseException):
    """Used when an urgent robot stop is triggered"""


class RobotLockedException(BaseException):
    """Exception that is produced when another instance of a robot is running"""


class SshNotConnectedException(BaseException):
    """Exception that is produced trying to interact with a disconnected SSH client"""
