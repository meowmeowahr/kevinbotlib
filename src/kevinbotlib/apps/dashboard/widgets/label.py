from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsProxyWidget, QLabel

from kevinbotlib.apps.dashboard.helpers import get_structure_text
from kevinbotlib.apps.dashboard.widgets.base import WidgetItem
from kevinbotlib.comm import RedisCommClient

if TYPE_CHECKING:
    from kevinbotlib.apps.dashboard.app import GridGraphicsView


class LabelWidgetItem(WidgetItem):
    def __init__(
        self,
        title: str,
        key: str,
        options: dict,
        grid: "GridGraphicsView",
        span_x=1,
        span_y=1,
        _client: RedisCommClient | None = None,
    ):
        super().__init__(title, key, options, grid, span_x, span_y)
        self.kind = "text"

        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet(f"background: transparent; color: {self.view.theme.value.foreground}")

        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(self.label)

        self.update_label_geometry()

    def update_label_geometry(self):
        # Position the label below the title bar
        label_margin = self.margin + 30  # 30 is the title bar height
        self.proxy.setGeometry(
            self.margin, label_margin, self.width - 2 * self.margin, self.height - label_margin - self.margin
        )

    def set_span(self, x, y):
        super().set_span(x, y)
        self.update_label_geometry()

    def prepareGeometryChange(self):  # noqa: N802
        super().prepareGeometryChange()
        self.update_label_geometry()

    def update_data(self, data: dict):
        super().update_data(data)
        self.label.setText(get_structure_text(data))
        label_margin = self.margin + 30  # 30 is the title bar height
        self.proxy.setGeometry(
            self.margin, label_margin, self.width - 2 * self.margin, self.height - label_margin - self.margin
        )
