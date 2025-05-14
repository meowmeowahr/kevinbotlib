from kevinbotlib.hardware.interfaces.serial import RawSerialInterface


class RawKeyValueSerialController:
    """A controller for managing key-value pairs over a raw serial interface"""

    def __init__(self, interface: RawSerialInterface, delimeter: bytes = b"=", terminator: bytes = b"\n") -> None:
        """Initialize the controller with a serial interface

        Args:
            interface (RawSerialInterface): The serial interface to use
            delimeter (bytes): Key-value delimeter
            terminator (bytes): EOL character
        """
        self._iface = interface
        self._delimiter = delimeter
        self._terminator = terminator

    def write(self, key: bytes, value: bytes | None = None) -> int | None:
        """Send a key-value pair over the serial connection

        Args:
            key (bytes): The key to set
            value (bytes | None): The value to associate with the key. If no value is provided, will not send a delimeter. Defaults to None.

        Returns:
            int | None: Number of bytes written
        """
        message = key + self._delimiter + value + self._terminator if value else key + self._terminator
        return self._iface.write(message)

    def read(self) -> tuple[bytes, bytes] | None:
        """Read the next key-value pair from the serial connection

        Returns:
            tuple[bytes, bytes] | None: (key, value) tuple if successful, None otherwise
        """
        if not self._iface.is_open:
            return None

        line = self._iface.read_until(self._terminator)

        if self._delimiter not in line:
            return (line.rstrip(self._terminator), b"")
        if line and self._delimiter in line:
            key, value = line.split(self._delimiter, 1)
            value = value.rstrip(self._terminator)
            return (key, value)
        return None

    @property
    def is_connected(self) -> bool:
        """Check if the serial connection is active

        Returns:
            bool: Connection status
        """
        return self._iface.is_open

    @property
    def interface(self) -> RawSerialInterface:
        """Get the serial interface

        Returns:
            RawSerialInterface: Serial interface
        """
        return self._iface
