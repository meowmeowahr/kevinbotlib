class SerialPortOpenFailure(BaseException):
    """Raised on failure to open serial port"""


class BaseSerialTimeoutException(BaseException):
    """Raised on a serial operation timeout"""


class SerialWriteTimeout(BaseSerialTimeoutException):
    """Raised on a serial write timeout"""
