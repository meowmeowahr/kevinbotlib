from abc import ABC, abstractmethod
from typing import Any, final

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget


class WindowView(QObject):
    """
    Simulator Subwindow using PySide6 widgets.
    """

    @property
    def title(self) -> str:
        """
        Title for the WindowView.

        Returns:
            Title.
        """

        return f"New WindowView <{hex(self.__hash__())}>"

    def generate(self) -> QWidget:
        """
        Widget to display in the WindowView.

        Returns:
            PySide6 QWidget.
        """
        raise NotImplementedError

    def update(self, payload: Any) -> None:
        """
        Update the widget with the given payload. To be manually implemented by the subclass.

        Args:
            payload: Payload from the main process.
        """

    @final
    def send_payload(self, payload: "WindowViewOutputPayload"):
        """
        Function to send a custom payload into the main process.

        **Implemented at runtime. Do not override.**

        Args:
            payload: Customized subclass of WindowViewOutputPayload.
        """


class WindowViewOutputPayload(ABC):
    """
    A payload from the WindowView to the main process.
    """

    @abstractmethod
    def payload(self) -> Any:
        """
        Payload content.

        Returns:
            Payload.
        """
        raise NotImplementedError


WINDOW_VIEW_REGISTRY: dict[str, type[WindowView]] = {}


def register_window_view(winid: str):
    """
    Register a WindowView subclass into the Simulation Framework.

    Args:
        winid: WindowView ID.
    """

    def decorator(cls: type[WindowView]):
        WINDOW_VIEW_REGISTRY[winid] = cls
        return cls

    return decorator
