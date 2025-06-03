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
