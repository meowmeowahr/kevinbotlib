from enum import Enum

import blake3


def get_structure_text(value: dict | None):
    return str(value["value"]) if value else "None"


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


class Colors(Enum):
    Red = "#b44646"
    Green = "#46b482"
    Blue = "#4682b4"
    White = "#e4e4e4"
    Black = "#060606"
    Yellow = "#e4e446"
    Magenta = "#b446b4"
