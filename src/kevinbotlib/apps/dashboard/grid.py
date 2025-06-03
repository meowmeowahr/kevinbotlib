import functools
from collections.abc import Callable

from PySide6.QtCore import QObject, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
)

from kevinbotlib.apps.dashboard.grid_theme import Themes as GridThemes
from kevinbotlib.apps.dashboard.widgets.base import WidgetItem


class GridGraphicsView(QGraphicsView):
    def __init__(self, parent=None, grid_size: int = 48, rows=10, cols=10, theme: GridThemes = GridThemes.Dark):
        super().__init__(parent)
        self.grid_size = grid_size
        self.rows, self.cols = rows, cols
        self.theme = theme

        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setCacheMode(QGraphicsView.CacheModeFlag.CacheBackground)
        self.setOptimizationFlags(
            QGraphicsView.OptimizationFlag.IndirectPainting | QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing
        )
        self.setBackgroundBrush(QColor(theme.value.background))

        self.grid_lines = []
        self.draw_grid()

        self.highlight_rect = self.scene().addRect(
            0, 0, self.grid_size, self.grid_size, QPen(Qt.PenStyle.NoPen), QBrush(QColor(0, 255, 0, 100))
        )
        self.highlight_rect.setZValue(3)
        self.highlight_rect.hide()

    def set_theme(self, theme: GridThemes):
        self.theme = theme
        self.setBackgroundBrush(QColor(theme.value.background))
        self.update()

    def is_valid_drop_position(self, position, dragging_widget=None, span_x=1, span_y=1):
        grid_size = self.grid_size
        rows, cols = self.rows, self.cols
        new_x = round(position.x() / grid_size) * grid_size
        new_y = round(position.y() / grid_size) * grid_size
        new_x = max(0, min(new_x, (cols - span_x) * grid_size))
        new_y = max(0, min(new_y, (rows - span_y) * grid_size))
        if new_x + span_x * grid_size > cols * grid_size or new_y + span_y * grid_size > rows * grid_size:
            return False
        bounding_rect = QRectF(QPointF(new_x, new_y), QSize(span_x * grid_size, span_y * grid_size))
        items = self.scene().items(bounding_rect)
        return all(not (isinstance(item, WidgetItem) and item != dragging_widget) for item in items)

    def update_highlight(self, position, dragging_widget=None, span_x=1, span_y=1):
        grid_size = self.grid_size
        rows, cols = self.rows, self.cols
        new_x = round(position.x() / grid_size) * grid_size
        new_y = round(position.y() / grid_size) * grid_size
        new_x = max(0, min(new_x, (cols - span_x) * grid_size))
        new_y = max(0, min(new_y, (rows - span_y) * grid_size))
        valid_position = self.is_valid_drop_position(position, dragging_widget, span_x, span_y)
        self.highlight_rect.setBrush(QBrush(QColor(0, 255, 0, 100) if valid_position else QColor(255, 0, 0, 100)))
        self.highlight_rect.setRect(new_x, new_y, grid_size * span_x, grid_size * span_y)
        self.highlight_rect.show()

    def hide_highlight(self):
        self.highlight_rect.hide()

    def draw_grid(self):
        for item in reversed(self.grid_lines):
            self.scene().removeItem(item)
            self.grid_lines.remove(item)

        grid_size = self.grid_size
        rows, cols = self.rows, self.cols
        pen = QPen(QColor(self.theme.value.border), 1, Qt.PenStyle.DashLine)
        for i in range(cols + 1):
            x = i * grid_size
            self.grid_lines.append(self.scene().addLine(x, 0, x, rows * grid_size, pen))
        for i in range(rows + 1):
            y = i * grid_size
            self.grid_lines.append(self.scene().addLine(0, y, cols * grid_size, y, pen))
        self.scene().setSceneRect(0, 0, cols * grid_size, rows * grid_size)

    def set_grid_size(self, size: int):
        self.grid_size = size
        self.draw_grid()
        self.highlight_rect = self.scene().addRect(
            0, 0, self.grid_size, self.grid_size, QPen(Qt.PenStyle.NoPen), QBrush(QColor(0, 255, 0, 100))
        )
        self.highlight_rect.setZValue(3)
        self.highlight_rect.hide()
        for item in self.scene().items():
            if isinstance(item, WidgetItem):
                old_x = item.pos().x() // item.grid_size
                old_y = item.pos().y() // item.grid_size
                item.grid_size = size
                item.set_span(item.span_x, item.span_y)
                item.setPos(old_x * self.grid_size, old_y * self.grid_size)

    def can_resize_to(self, new_rows, new_cols):
        """Check if all current widgets would fit in the new dimensions"""
        for item in self.scene().items():
            if not isinstance(item, WidgetItem):
                continue
            if (
                item.pos().x() + item.span_x * self.grid_size > new_cols * self.grid_size
                or item.pos().y() + item.span_y * self.grid_size > new_rows * self.grid_size
            ):
                return False
        return True

    def resize_grid(self, rows, cols):
        """Attempt to resize the grid while preserving widget instances"""
        # First check if resize is possible
        if not self.can_resize_to(rows, cols):
            return False

        widgets = [item for item in self.scene().items() if isinstance(item, WidgetItem)]

        for widget in widgets:
            self.scene().removeItem(widget)

        self.scene().clear()
        self.grid_lines.clear()

        self.rows = rows
        self.cols = cols

        self.draw_grid()

        self.highlight_rect = self.scene().addRect(
            0, 0, self.grid_size, self.grid_size, QPen(Qt.PenStyle.NoPen), QBrush(QColor(0, 255, 0, 100))
        )
        self.highlight_rect.setZValue(3)
        self.highlight_rect.hide()

        for widget in widgets:
            self.scene().addItem(widget)

        return True


class WidgetGridController(QObject):
    def __init__(self, view: GridGraphicsView) -> None:
        super().__init__()
        self.view: GridGraphicsView = view

    def add(self, item: WidgetItem):
        grid_size = self.view.grid_size
        rows, cols = self.view.rows, self.view.cols

        # Calculate final spans before position checking
        final_span_x = max(item.span_x, ((item.min_width + self.view.grid_size - 1) // self.view.grid_size))
        final_span_y = max(item.span_y, ((item.min_height + self.view.grid_size - 1) // self.view.grid_size))

        # Pre-apply the spans to ensure correct collision detection
        item.set_span(final_span_x, final_span_y)

        # Iterate through possible positions with corrected spans
        for row in range(rows - final_span_y + 1):
            for col in range(cols - final_span_x + 1):
                test_pos = QPointF(col * grid_size, row * grid_size)

                # Create a rect that covers the entire final span area
                span_rect = QRectF(
                    test_pos,
                    QPointF(test_pos.x() + (final_span_x * grid_size), test_pos.y() + (final_span_y * grid_size)),
                )

                # Temporarily position the item for accurate collision testing
                original_pos = item.pos()
                item.setPos(test_pos)

                # Get all items at the test position
                colliding_items = [
                    i for i in self.view.scene().items(span_rect) if isinstance(i, WidgetItem) and i != item
                ]

                # Reset position
                item.setPos(original_pos)

                if not colliding_items:
                    # Position is valid, place the widget
                    item.setPos(test_pos)
                    self.view.scene().addItem(item)
                    item.item_deleted.connect(functools.partial(self.remove_widget))
                    return

        # If we get here, no valid position was found

    def add_to_pos(self, item: WidgetItem, x, y):
        grid_size = self.view.grid_size
        item.setPos(x * grid_size, y * grid_size)
        self.view.scene().addItem(item)
        item.item_deleted.connect(functools.partial(self.remove_widget))

    def remove_widget(self, widget):
        self.view.scene().removeItem(widget)

    def get_widgets(self) -> list[dict]:
        widgets = []
        for item in self.view.scene().items():
            if isinstance(item, WidgetItem):
                widget_info = {
                    "pos": (item.pos().x() // item.grid_size, item.pos().y() // item.grid_size),
                    "span_x": item.span_x,
                    "span_y": item.span_y,
                    "kind": item.kind,
                    "title": item.title,
                    "options": item.options,
                    "key": item.key,
                }
                widgets.append(widget_info)
        return widgets

    def update_widgets_data(self, raw_data):
        """Update all widgets with fresh data and force view refresh"""
        for item in self.get_items():
            if item.key in raw_data:
                item.update_data(raw_data[item.key])

        # Force the view to update after all widget updates
        self.view.viewport().update()

    def get_items(self) -> list[WidgetItem]:
        return [item for item in self.view.scene().items() if isinstance(item, WidgetItem)]

    def load(self, loader: Callable[[dict], WidgetItem], items: list[dict]):
        for item in items:
            widget_item = loader(item)
            self.add_to_pos(widget_item, item["pos"][0], item["pos"][1])
