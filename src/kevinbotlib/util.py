def fullclassname(o: object) -> str:
    module = o.__module__
    if module == 'builtins':
        return o.__qualname__ # avoid outputs like 'builtins.str'
    return module + '.' + o.__qualname__