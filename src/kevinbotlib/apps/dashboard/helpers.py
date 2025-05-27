import blake3


def get_structure_text(value: dict | None):
    if not value:
        return ""
    out = ""
    if "did" in value and value["did"] in [
        "kevinbotlib.vision.dtype.mjpeg",
        "kevinbotlib.vision.dtype.frame",
        "kevinbotlib.dtype.bin",
    ]:
        return f"BLAKE3 Hash of Value: {blake3.blake3(value['value'].encode()).hexdigest()}"
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


def find_diff_indices(old: str, new: str) -> tuple[int, int, int, int]:
    start = 0
    while start < len(old) and start < len(new) and old[start] == new[start]:
        start += 1

    end_old = len(old)
    end_new = len(new)
    while end_old > start and end_new > start and old[end_old - 1] == new[end_new - 1]:
        end_old -= 1
        end_new -= 1

    return start, end_old, start, end_new
