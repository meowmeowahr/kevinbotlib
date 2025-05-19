from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QStyleOptionGraphicsItem, QWidget

from kevinbotlib.apps.dashboard.widgets.base import WidgetItem
from kevinbotlib.comm import (
    RedisCommClient,
)

if TYPE_CHECKING:
    from kevinbotlib.apps.dashboard.app import GridGraphicsView


class ColorWidgetItem(WidgetItem):
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
        self.kind = "color"
        self.min_width = self.grid_size  # Minimum width in pixels
        self.min_height = self.grid_size * 2  # Minimum height in pixels

        self.raw_data = {}
        self.client = client

    def paint(self, painter: QPainter, _option: QStyleOptionGraphicsItem, /, _widget: QWidget | None = None):  # type: ignore
        super().paint(painter, _option, _widget)

        # Draw boolean as a rectangle of red or green
        painter.setBrush(QColor(self.raw_data.get("value", "#ffffff")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.boundingRect().adjusted(10, 40, -10, -10), 5, 5)

    def update_data(self, data: dict):
        super().update_data(data)
        self.raw_data = data
        self.update()

    def close(self):
        super().close()
