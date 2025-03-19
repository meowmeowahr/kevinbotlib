from enum import StrEnum

import serial
import serial.tools
import serial.tools.list_ports
from pydantic.dataclasses import dataclass

from kevinbotlib.hardware.interfaces.exceptions import SerialPortOpenFailure, SerialWriteTimeout


@dataclass
class SerialDeviceInfo:
    device: str
    device_path: str | None
    name: str
    description: str
    manufacturer: str | None
    pid: int | None
    hwid: str


class SerialIdentification:
    """Identify serial ports"""

    @staticmethod
    def list_device_info() -> list[SerialDeviceInfo]:
        """List to available connected serial ports

        Returns:
            list[SerialDeviceInfo]: List of port info
        """
        return [
            SerialDeviceInfo(
                port.device, port.device_path, port.name, port.description, port.manufacturer, port.pid, port.hwid
            )
            for port in serial.tools.list_ports.comports()
        ]


class SerialParity(StrEnum):
    NONE = serial.PARITY_NONE
    EVEN = serial.PARITY_EVEN
    ODD = serial.PARITY_ODD
    MARK = serial.PARITY_MARK
    SPACE = serial.PARITY_SPACE


class RawSerialInterface:
    """Raw serial interface"""

    def __init__(
        self,
        port: str | None = None,
        baudrate: int = 9600,
        bytesize: int = 8,
        parity: SerialParity = SerialParity.NONE,
        stopbits: float = 1,
        timeout: float | None = None,
        write_timeout: float | None = None,
        inter_byte_timeout: float | None = None,
        *,
        xonxoff: bool = False,
        rtscts: bool = False,
        dsrdtr: bool = False,
        exclusive: bool | None = None,
    ):
        """Initialize a new serial port connection

        Args:
            port (str | None, optional): The device to connect to e.g. COM3 of /dev/ttyAMA0. Defaults to None.
            baudrate (int, optional): The baud rate to utilize. Defaults to 9600.
            bytesize (int, optional): Size of each byte to be sent. The default works for most use cases. Defaults to 8.
            parity (SerialParity, optional): Parity type. Defaults to SerialParity.NONE.
            stopbits (float, optional): Number of stop bits to utilize. Defaults to 1.
            timeout (float | None, optional): Read timeout in seconds. Defaults to None.
            write_timeout (float | None, optional): Write timeout in seconds. Defaults to None.
            inter_byte_timeout (float | None, optional): Timeout between characters. Set to None to disable. Defaults to None.
            xonxoff (bool, optional): Enable software flow control. Defaults to False.
            rtscts (bool, optional): Enable hardware RTS/CTS flow control. Defaults to False.
            dsrdtr (bool, optional): Enable hardware DSR/DTR flow control. Defaults to False.
            exclusive (bool | None, optional): POSIX exclusive access mode. Defaults to None.
        """
        self._serial = serial.Serial(
            port,
            baudrate,
            bytesize,
            parity,
            stopbits,
            timeout,
            xonxoff,
            rtscts,
            write_timeout,
            dsrdtr,
            inter_byte_timeout,
            exclusive,
        )

    def __del__(self):
        self._serial.close()

    @property
    def port(self) -> str | None:
        """The serial port device name (e.g., COM3 or /dev/ttyAMA0)"""
        return self._serial.port

    @port.setter
    def port(self, value: str | None) -> None:
        self._serial.port = value

    @property
    def baudrate(self) -> int:
        """The baud rate of the serial connection in bits per second"""
        return self._serial.baudrate

    @baudrate.setter
    def baudrate(self, value: int) -> None:
        self._serial.baudrate = value

    @property
    def bytesize(self) -> int:
        """The number of bits per byte (typically 8)"""
        return self._serial.bytesize

    @bytesize.setter
    def bytesize(self, value: int) -> None:
        self._serial.bytesize = value

    @property
    def parity(self) -> SerialParity:
        """The parity checking mode (e.g., NONE, EVEN, ODD)"""
        return SerialParity(self._serial.parity)

    @parity.setter
    def parity(self, value: SerialParity) -> None:
        self._serial.parity = value

    @property
    def stopbits(self) -> float:
        """The number of stop bits (typically 1 or 2)"""
        return self._serial.stopbits

    @stopbits.setter
    def stopbits(self, value: float) -> None:
        self._serial.stopbits = value

    @property
    def timeout(self) -> float | None:
        """The read timeout value in seconds (None for no timeout)"""
        return self._serial.timeout

    @timeout.setter
    def timeout(self, value: float | None) -> None:
        self._serial.timeout = value

    @property
    def write_timeout(self) -> float | None:
        """The write timeout value in seconds (None for no timeout)"""
        return self._serial.write_timeout

    @write_timeout.setter
    def write_timeout(self, value: float | None) -> None:
        self._serial.write_timeout = value

    @property
    def inter_byte_timeout(self) -> float | None:
        """The timeout between bytes in seconds (None to disable)"""
        return self._serial.inter_byte_timeout

    @inter_byte_timeout.setter
    def inter_byte_timeout(self, value: float | None) -> None:
        self._serial.inter_byte_timeout = value

    @property
    def xonxoff(self) -> bool:
        """Whether software flow control (XON/XOFF) is enabled"""
        return self._serial.xonxoff

    @xonxoff.setter
    def xonxoff(self, value: bool) -> None:
        self._serial.xonxoff = value

    @property
    def rtscts(self) -> bool:
        """Whether hardware RTS/CTS flow control is enabled"""
        return self._serial.rtscts

    @rtscts.setter
    def rtscts(self, value: bool) -> None:
        self._serial.rtscts = value

    @property
    def dsrdtr(self) -> bool:
        """Whether hardware DSR/DTR flow control is enabled"""
        return self._serial.dsrdtr

    @dsrdtr.setter
    def dsrdtr(self, value: bool) -> None:
        self._serial.dsrdtr = value

    @property
    def exclusive(self) -> bool | None:
        """Whether POSIX exclusive access mode is enabled (None for platform default)"""
        return self._serial.exclusive

    @exclusive.setter
    def exclusive(self, value: bool | None) -> None:
        self._serial.exclusive = value

    def open(self):
        try:
            self._serial.open()
        except serial.SerialException as e:
            raise SerialPortOpenFailure(*e.args) from e

    def read(self, n: int = 1) -> bytes:
        """
        Reads `n` bytes from the serial port

        Blocks until `n` number of bytes are read, or read timeout

        May return fewer than `n` characters on timeout

        Args:
            n (int, optional): Number of bytes to read. Defaults to 1.

        Returns:
            bytes: Character array
        """
        return self._serial.read(n)

    def read_until(self, term: bytes = b"\n", size: int | None = None) -> bytes:
        """
        Reads until `term` is found, `size` bytes is reached, or read timeout

        Args:
            term (bytes, optional): Termination bytes. Defaults to b'\n'.
            size (int | None, optional): Maximum bytes to read. Defaults to None.

        Returns:
            bytes: Character array
        """
        return self._serial.read_until(term, size)

    def write(self, data: bytes) -> int | None:
        """Write bytes to the serial port

        Args:
            data (bytes): Bytes to write

        Returns:
            int | None: Number of bytes written
        """
        try:
            return self._serial.write(data)
        except serial.SerialTimeoutException as e:
            raise SerialWriteTimeout(*e.args) from e

    def flush(self):
        """Wait until all serial data is written"""
        self._serial.flush()
