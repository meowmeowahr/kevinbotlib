from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QGraphicsProxyWidget, QLabel

from kevinbotlib.apps.dashboard.helpers import get_structure_text
from kevinbotlib.apps.dashboard.widgets.base import WidgetItem
from kevinbotlib.comm import RedisCommClient

if TYPE_CHECKING:
    from kevinbotlib.apps.dashboard.app import GridGraphicsView


class BigLabelWidgetItem(WidgetItem):
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
        self.kind = "bigtext"

        self.label = QLabel()
        self.label.setWordWrap(False)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet(f"background: transparent; color: {self.view.theme.value.foreground}")

        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(self.label)

        self.update_label_geometry()
        self.adjust_font_size_to_fit()

    def update_label_geometry(self):
        label_margin = self.margin + 30  # 30 is the title bar height
        self.label_rect = (
            self.margin,
            label_margin,
            self.width - 2 * self.margin,
            self.height - label_margin - self.margin,
        )
        self.proxy.setGeometry(*self.label_rect)

    def set_span(self, x, y):
        super().set_span(x, y)
        self.adjust_font_size_to_fit()
        self.update_label_geometry()

    def prepareGeometryChange(self):  # noqa: N802
        super().prepareGeometryChange()
        self.adjust_font_size_to_fit()
        self.update_label_geometry()

    def update_data(self, data: dict):
        super().update_data(data)
        old = self.label.text()
        new = get_structure_text(data)
        self.label.setText(new)
        if old != new:
            self.adjust_font_size_to_fit()

    def adjust_font_size_to_fit(self):
        if not self.label.text():
            return

        max_width = self.label_rect[2]
        max_height = self.label_rect[3]
        text = self.label.text()

        font = QFont(self.label.font())
        min_size = 4
        max_size = 200

        best_size = min_size

        # Binary search for optimal font size
        while min_size <= max_size:
            mid = (min_size + max_size) // 2
            font.setPointSize(mid)
            metrics = QFontMetrics(font)
            rect = metrics.boundingRect(text)

            if rect.width() <= max_width and rect.height() <= max_height:
                best_size = mid
                min_size = mid + 1
            else:
                max_size = mid - 1

        font.setPointSize(best_size - 2)
        self.label.setFont(font)
