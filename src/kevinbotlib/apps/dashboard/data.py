def raw_to_string(raw: dict):
    if "value" in raw:
        return str(raw["value"])
    return "Error"
