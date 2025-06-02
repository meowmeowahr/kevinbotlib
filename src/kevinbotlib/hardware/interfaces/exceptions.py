class SerialPortOpenFailure(BaseException):
    """Exception that is raised on failure to open serial port"""


class BaseSerialTimeoutException(BaseException):
    """Exception that is raised on a serial operation timeout"""


class SerialWriteTimeout(BaseSerialTimeoutException):
    """Exception that is raised on a serial write timeout"""


class SerialException(BaseException):
    """Exception that is raised on a general serial communication failure"""
