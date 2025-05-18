from dataclasses import dataclass
from enum import Enum


@dataclass
class ThemeOptions:
    background: str
    item_background: str
    foreground: str
    primary: str
    border: str
    padding: int = 4


class Themes(Enum):
    Dark = ThemeOptions(
        background="#0a1316",
        item_background="#151d21",
        foreground="#d0d8d8",
        primary="#4682b4",
        border="#2d3639",
    )
    Light = ThemeOptions(
        background="#ffffff",
        item_background="#dcdcdc",
        foreground="#333333",
        primary="#4682b4",
        border="#d5d5d5",
    )
