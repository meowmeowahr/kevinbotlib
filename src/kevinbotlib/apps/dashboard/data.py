def get_structure_text(value: dict | None):
    if not value:
        return ""
    out = ""
    if "struct" in value and "dashboard" in value["struct"]:
        for viewable in value["struct"]["dashboard"]:
            display = ""
            if "element" in viewable:
                raw = value[viewable["element"]]
                if "format" in viewable:
                    fmt = viewable["format"]
                    if fmt == "percent":
                        display = f"{raw * 100:.2f}%"
                    elif fmt == "degrees":
                        display = f"{raw}°"
                    elif fmt == "radians":
                        display = f"{raw} rad"
                    elif fmt.startswith("limit:"):
                        limit = int(fmt.split(":")[1])
                        display = raw[:limit] + "..."
                    else:
                        display = raw
            out += str(display)
    return out
