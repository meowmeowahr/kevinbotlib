import io
from enum import StrEnum

import serial
import serial.tools
import serial.tools.list_ports
from pydantic.dataclasses import dataclass

from kevinbotlib.hardware.interfaces.exceptions import SerialException, SerialPortOpenFailure, SerialWriteTimeout


@dataclass
class SerialDeviceInfo:
    """Information about a serial device link."""

    device: str
    """Device"""

    device_path: str | None
    """Device path. Ex: /dev/ttyAMA0."""

    name: str
    """Device name."""

    description: str
    """Device description."""

    manufacturer: str | None
    """Device manufacturer."""

    pid: int | None
    """Device PID."""

    hwid: str
    """Device HWID."""


class SerialIdentification:
    """Identify serial ports"""

    @staticmethod
    def list_device_info() -> list[SerialDeviceInfo]:
        """List of available connected serial ports

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
    """Serial parity types"""

    NONE = serial.PARITY_NONE
    """No parity checking."""

    EVEN = serial.PARITY_EVEN
    """Even parity checking."""

    ODD = serial.PARITY_ODD
    """Odd parity checking."""

    MARK = serial.PARITY_MARK
    """Mark parity checking."""

    SPACE = serial.PARITY_SPACE
    """Space parity checking."""


class RawSerialInterface(io.IOBase):
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

    # * connection

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
        """Attempt to open the serial port

        Raises:
            SerialPortOpenFailure: Port failed to open
        """
        try:
            self._serial.open()
        except serial.SerialException as e:
            raise SerialPortOpenFailure(*e.args) from e

    @property
    def is_open(self) -> bool:
        """Is the serial port open?

        Returns:
            bool: Open state
        """
        return self._serial.is_open

    # * read

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

    # * write

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
        except serial.SerialException as e:
            raise SerialException(*e.args) from e

    def flush(self):
        """Wait until all serial data is written"""
        self._serial.flush()

    # * buffer control

    @property
    def in_waiting(self) -> int:
        """Get the number of bytes in the transmit buffer

        Returns:
            int: Number of bytes
        """
        return self._serial.in_waiting

    @property
    def out_waiting(self) -> int:
        """Get the number of bytes in the receive buffer

        Returns:
            int: Number of bytes
        """
        return self._serial.out_waiting

    def reset_input_buffer(self) -> None:
        """Clear the input buffer, delete and ignore all data"""
        self._serial.reset_input_buffer()

    def reset_output_buffer(self) -> None:
        """Clear the output buffer, delete and ignore all data"""
        self._serial.reset_output_buffer()

    def reset_buffers(self) -> None:
        """Reset input and output buffers, delete and ignore all data"""
        self.reset_input_buffer()
        self.reset_output_buffer()

    # * line conditions

    def send_break(self, duration: float = 0.25) -> None:
        """Send the break condition for `duration`, then return to idle state

        Args:
            duration (float, optional): Seconds for BREAK condition. Defaults to 0.25.
        """
        self._serial.send_break(duration)

    @property
    def break_condition(self) -> bool:
        """Serial `BREAK` condition, no transmit when active

        Returns:
            bool: BREAK condition
        """
        return self._serial.break_condition

    @break_condition.setter
    def break_condition(self, bk: bool):
        self._serial.break_condition = bk

    @property
    def rts(self) -> bool:
        """Serial `RTS` line, setting before connecting is possible

        Returns:
            bool: RTS
        """
        return self._serial.rts

    @rts.setter
    def rts(self, rts: bool):
        self._serial.rts = rts

    @property
    def dtr(self) -> bool:
        """Serial `DTR` line, setting before connecting is possible

        Returns:
            bool: DTR
        """
        return self._serial.dtr

    @dtr.setter
    def dtr(self, dtr: bool):
        self._serial.dtr = dtr

    @property
    def cts(self) -> bool:
        """Get the state if the `CTS` line

        Returns:
            bool: CTS state
        """
        return self._serial.cts

    @property
    def ri(self) -> bool:
        """Get the state if the `RI` line

        Returns:
            bool: RI state
        """
        return self._serial.ri

    @property
    def cd(self) -> bool:
        """Get the state if the `CD` line

        Returns:
            bool: CD state
        """
        return self._serial.cd

    # * misc
    @property
    def device_name(self) -> str | None:
        """Device name

        Returns:
            str | None: Device name, if available
        """
        return self._serial.name
