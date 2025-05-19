from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGraphicsProxyWidget, QLineEdit

from kevinbotlib.apps.dashboard.helpers import find_diff_indices, get_structure_text
from kevinbotlib.apps.dashboard.widgets.base import WidgetItem
from kevinbotlib.comm import (
    FloatSendable,
    IntegerSendable,
    RedisCommClient,
    StringSendable,
)
from kevinbotlib.logger import Logger

if TYPE_CHECKING:
    from kevinbotlib.apps.dashboard.app import GridGraphicsView


class TextEditWidgetItem(WidgetItem):
    setdata = Signal(str)

    def __init__(
        self,
        title: str,
        key: str,
        options: dict,
        grid: "GridGraphicsView",
        span_x=1,
        span_y=1,
        client: RedisCommClient | None = None,
    ):
        super().__init__(title, key, options, grid, span_x, span_y)
        self.kind = "textedit"
        self.raw_data = {}
        self.client = client

        self.line_edit = QLineEdit()
        self.line_edit.setStyleSheet(self.view.window().styleSheet())
        self.line_edit.setPlaceholderText("Enter text...")
        self.line_edit.editingFinished.connect(self.commit)

        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(self.line_edit)

        self.setdata.connect(self.set_text)
        self.update_line_edit_geometry()

    def update_line_edit_geometry(self):
        if not self.proxy or not self.line_edit:
            return

        br = self.boundingRect()
        le_size = self.proxy.size()

        # Center horizontally and vertically
        x = (br.width() - le_size.width()) / 2
        y = (br.height() + 30 - le_size.height()) / 2
        self.proxy.setPos(x, y)

    def set_span(self, x, y):
        super().set_span(x, y)
        self.update_line_edit_geometry()

    def prepareGeometryChange(self):  # noqa: N802
        super().prepareGeometryChange()
        self.update_line_edit_geometry()

    def set_text(self, text: str):
        old = self.line_edit.text()
        if text != old:
            self.line_edit.blockSignals(True)
            self.line_edit.setText(text)
            self.line_edit.blockSignals(False)

    def update_data(self, data: dict):
        super().update_data(data)
        self.raw_data = data
        self.setdata.emit(get_structure_text(data))

    def commit(self):
        text = self.line_edit.text()
        self.commit_edit(text)

    def commit_edit(self, text: str):
        if not self.client or not self.client.is_connected() or not self.raw_data:
            return

        try:
            match self.raw_data["did"]:
                case "kevinbotlib.dtype.str":
                    self.client.set(
                        self.key,
                        StringSendable(
                            value=text,
                            struct=self.raw_data["struct"],
                            timeout=self.raw_data["timeout"],
                            flags=self.raw_data.get("flags", []),
                        ),
                    )
                case "kevinbotlib.dtype.int":
                    self.client.set(
                        self.key,
                        IntegerSendable(
                            value=int(text),
                            struct=self.raw_data["struct"],
                            timeout=self.raw_data["timeout"],
                            flags=self.raw_data.get("flags", []),
                        ),
                    )
                case "kevinbotlib.dtype.float":
                    self.client.set(
                        self.key,
                        FloatSendable(
                            value=float(text),
                            struct=self.raw_data["struct"],
                            timeout=self.raw_data["timeout"],
                            flags=self.raw_data.get("flags", []),
                        ),
                    )
                case _:
                    Logger().error(f"Unsupported dtype for editing: {self.raw_data['did']}")
        except ValueError:
            Logger().warning(f"Invalid value for type '{self.raw_data['did']}': {text}")

    def close(self):
        pass
