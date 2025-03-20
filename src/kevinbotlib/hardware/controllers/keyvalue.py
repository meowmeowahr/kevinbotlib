from kevinbotlib.hardware.interfaces.serial import RawSerialInterface


class RawKeyValueSerialController:
    """A controller for managing key-value pairs over a raw serial interface"""

    def __init__(self, interface: RawSerialInterface, delimeter: bytes = b"=", terminator: bytes = b"\n"):
        """Initialize the controller with a serial interface

        Args:
            interface (RawSerialInterface): The serial interface to use
            delimeter (bytes): Key-value delimeter
            terminator (bytes): EOL character
        """
        self._iface = interface
        self._delimiter = delimeter
        self._terminator = terminator

    def send_value(self, key: str, value: str) -> int | None:
        """Send a key-value pair over the serial connection

        Args:
            key (str): The key to set
            value (str): The value to associate with the key

        Returns:
            int | None: Number of bytes written
        """
        message = f"{key}{self._delimiter.decode()}{value}".encode() + self._terminator
        return self._iface.write(message)

    def read_value(self) -> tuple[bytes, bytes] | None:
        """Read the next key-value pair from the serial connection

        Returns:
            tuple[bytes, bytes] | None: (key, value) tuple if successful, None otherwise
        """
        if not self._iface.is_open:
            return None

        line = self._iface.readline()

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
