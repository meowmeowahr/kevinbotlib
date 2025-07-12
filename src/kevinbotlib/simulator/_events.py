from typing import TYPE_CHECKING, Any

from kevinbotlib.simulator.windowview import WindowViewOutputPayload

if TYPE_CHECKING:
    from kevinbotlib.simulator.windowview import WindowView


class _SimulatorInputEvent:
    pass


class _SimulatorOutputEvent:
    pass


class _SimulatorExitEvent(_SimulatorOutputEvent):
    pass


class _WindowViewUpdateEvent(_SimulatorInputEvent):
    """
    Sent **from the main process** → **GUI process**.

    Parameters
    ----------
    view_name : str
        The name that was passed to `SimMainWindow.add_window(...)`.
    payload : Any
        Arbitrary data that the WindowView's `update()` method
        knows how to interpret.
    """

    __slots__ = ("view_name", "payload")

    def __init__(self, view_name: str, payload: Any):
        self.view_name = view_name
        self.payload = payload


class _AddWindowEvent(_SimulatorInputEvent):
    def __init__(self, name: str, view_cls: type["WindowView"], *, default_open: bool = False):
        self.name = name
        self.view_cls = view_cls
        self.default_open = default_open


class _RobotProcessEndEvent(_SimulatorInputEvent):
    pass


class _ExitSimulatorEvent(_SimulatorInputEvent):
    pass


class _WindowViewPayloadEvent(_SimulatorOutputEvent):
    __slots__ = ("winid", "payload")

    def __init__(self, winid: str, payload: WindowViewOutputPayload):
        self.winid = winid
        self.payload = payload


class _WindowReadyEvent(_SimulatorOutputEvent):
    pass
