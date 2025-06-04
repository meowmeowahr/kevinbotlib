from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget


class WindowView(QObject):
    @property
    def title(self):
        return f"New WindowView <{hex(self.__hash__())}>"

    def generate(self) -> QWidget:  # unchanged
        raise NotImplementedError

    def update(self, payload):
        pass


WINDOW_VIEW_REGISTRY: dict[str, type[WindowView]] = {}


def register_window_view(name: str):
    def decorator(cls: type[WindowView]):
        WINDOW_VIEW_REGISTRY[name] = cls
        return cls

    return decorator
