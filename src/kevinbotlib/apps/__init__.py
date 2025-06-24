from superqt.fonticon import icon

dark_mode = False


def light():
    global dark_mode  # noqa: PLW0603
    dark_mode = False


def dark():
    global dark_mode  # noqa: PLW0603
    dark_mode = True


def get_icon(name, color: str | None = None):
    return icon(name, color=color if color else "white" if dark_mode else "black")
