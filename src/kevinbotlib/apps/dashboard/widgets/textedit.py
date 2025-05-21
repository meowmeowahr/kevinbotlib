from typing import TYPE_CHECKING

import qtawesome as qta
from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import (
    QGraphicsProxyWidget,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from kevinbotlib.apps.dashboard.helpers import get_structure_text
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
        self.current_value = ""

        self.container_widget = QWidget()
        self.container_widget.setStyleSheet("background: transparent;")
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(2)

        self.line_layout = QHBoxLayout()
        self.container_layout.addLayout(self.line_layout)

        self.line_edit = QLineEdit()
        self.line_edit.setStyleSheet(self.view.window().styleSheet())
        self.line_edit.setPlaceholderText("Enter text...")
        self.line_edit.textEdited.connect(self.on_text_edited)
        self.line_layout.addWidget(self.line_edit)

        self.validate_icon = qta.IconWidget()
        self.validate_icon.setIconSize(QSize(24, 24))
        self.validate_icon.setIcon(qta.icon("mdi6.close", color="#b34646"))
        self.line_layout.addWidget(self.validate_icon)

        self.actions_layout = QHBoxLayout()
        self.container_layout.addLayout(self.actions_layout)

        self.submit_button = QPushButton("Submit")
        self.submit_button.setStyleSheet(self.view.window().styleSheet())
        self.submit_button.clicked.connect(self.submit_clicked)
        self.submit_button.setIcon(qta.icon("mdi6.send"))
        self.actions_layout.addWidget(self.submit_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet(self.view.window().styleSheet())
        self.cancel_button.clicked.connect(self.cancel_clicked)
        self.cancel_button.setIcon(qta.icon("mdi6.cancel"))
        self.actions_layout.addWidget(self.cancel_button)

        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(self.container_widget)

        self.setdata.connect(self.update_text)
        self.update_line_edit_geometry()

    def update_line_edit_geometry(self):
        if not self.proxy or not self.container_widget:
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
        self.current_value = text
        self.line_edit.blockSignals(True)
        self.line_edit.setText(text)
        self.line_edit.blockSignals(False)
        self.validate_icon.setIcon(qta.icon("mdi6.check", color="#46b346"))

    def update_text(self, text: str):
        if self.current_value != self.line_edit.text():
            return
        self.set_text(text)

    def update_data(self, data: dict):
        super().update_data(data)
        self.raw_data = data
        self.setdata.emit(get_structure_text(data))

    def on_text_edited(self, _new_text: str):
        self.validate_icon.setIcon(qta.icon("mdi6.close", color="#b34646"))

    def submit_clicked(self):
        new_text = self.line_edit.text()
        if new_text != self.current_value:
            self.commit_edit(new_text)

    def cancel_clicked(self):
        self.set_text(self.current_value)

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
            self.set_text(text)  # Update current value after successful commit
        except ValueError:
            Logger().warning(f"Invalid value for type '{self.raw_data['did']}': {text}")

    def close(self):
        pass
