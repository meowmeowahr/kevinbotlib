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
