import socket
import sys


def fullclassname(o: object) -> str:
    """Get the full name of a class

    Args:
        o (object): The class to retrieve the full name of

    Returns:
        str: The name of the module and class
    """
    module = o.__module__
    if module == "builtins":
        return o.__qualname__  # avoid outputs like 'builtins.str'
    return module + "." + o.__qualname__


def is_binary() -> bool:
    """
    Detect if the application is running as a frozen executable or not.

    Returns:
        Is frozen?
    """
    return getattr(sys, "frozen", False)


def socket_exists(host: str = "localhost", port: int = 6379, timeout: float = 1.0) -> bool:
    """
    Check if a TCP socket exists
    Args:
        host: Host to check
        port: Port to check
        timeout: Socket connection timeout

    Returns:
        Socket exists?
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (TimeoutError, ConnectionRefusedError, OSError):
        return False
