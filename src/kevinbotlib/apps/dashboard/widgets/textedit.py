from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QGraphicsTextItem

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

        # Create QGraphicsTextItem instead of QLineEdit
        self.label = QGraphicsTextItem("", self)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self.label.setDefaultTextColor(self.view.theme.value.foreground)
        self.label.document().contentsChanged.connect(self.commit)

        self.setdata.connect(self.set_text)
        self.update_label_geometry()

    def update_label_geometry(self):
        label_margin: int = self.margin + 30
        self.label.setPos(self.margin, label_margin)
        self.label.setTextWidth(self.boundingRect().width() - 8)

    def set_span(self, x, y):
        super().set_span(x, y)
        self.update_label_geometry()

    def prepareGeometryChange(self):  # noqa: N802
        super().prepareGeometryChange()
        self.update_label_geometry()

    def set_text(self, text: str):
        old = self.label.toPlainText()
        if text == old:
            return

        self.label.document().setUndoRedoEnabled(False)
        self.label.document().blockSignals(True)

        cursor = self.label.textCursor()
        anchor = cursor.anchor()
        position = cursor.position()

        start_old, end_old, start_new, end_new = find_diff_indices(old, text)
        if start_old == end_old and start_new == end_new:
            return  # Already equal

        doc = self.label.document()
        edit_cursor = QTextCursor(doc)

        edit_cursor.beginEditBlock()
        edit_cursor.setPosition(start_old)
        edit_cursor.setPosition(end_old, QTextCursor.MoveMode.KeepAnchor)
        edit_cursor.insertText(text[start_new:end_new])
        edit_cursor.endEditBlock()

        # Restore original cursor position (approximate)
        new_cursor = self.label.textCursor()
        max_pos = doc.characterCount() - 1
        anchor = max(0, min(anchor, max_pos))
        position = max(0, min(position, max_pos))
        new_cursor.setPosition(anchor)
        new_cursor.setPosition(position, QTextCursor.MoveMode.KeepAnchor)
        self.label.setTextCursor(new_cursor)

        self.label.document().setUndoRedoEnabled(True)
        self.label.document().blockSignals(False)

    def update_data(self, data: dict):
        super().update_data(data)
        self.raw_data = data
        self.setdata.emit(get_structure_text(data))

    def commit(self):
        text = self.label.toPlainText()
        self.commit_edit(text)

    def commit_edit(self, text: str):
        if not self.client or not self.client.is_connected() or not self.raw_data:
            return

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

    def close(self):
        pass
