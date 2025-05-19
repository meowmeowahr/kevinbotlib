from abc import abstractmethod
from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, QRectF, Qt, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsObject, QInputDialog, QMenu, QStyleOptionGraphicsItem, QWidget

from kevinbotlib.comm import RedisCommClient

if TYPE_CHECKING:
    from kevinbotlib.apps.dashboard.app import GridGraphicsView


class WidgetItem(QGraphicsObject):
    item_deleted = Signal(object)

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
        super().__init__()

        self.kind = "base"
        self.options = options

        self.title = title
        self.key = key
        self.grid_size = grid.grid_size
        self.span_x = span_x
        self.span_y = span_y
        self.width = grid.grid_size * span_x
        self.height = grid.grid_size * span_y
        self.margin = grid.theme.value.padding
        self.setAcceptHoverEvents(True)
        self.setFlags(
            QGraphicsObject.GraphicsItemFlag.ItemIsMovable | QGraphicsObject.GraphicsItemFlag.ItemIsSelectable
        )
        self.setZValue(1)
        self.resizing = False
        self.resize_grip_size = 15
        self.min_width = self.grid_size * 2  # Minimum width in pixels
        self.min_height = self.grid_size * 2  # Minimum height in pixels
        self.view = grid

    def boundingRect(self):  # noqa: N802
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter: QPainter, _option: QStyleOptionGraphicsItem, /, _widget: QWidget | None = None):  # type: ignore
        painter.setBrush(QBrush(QColor(self.view.theme.value.item_background)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(
            QRect(self.margin, self.margin, self.width - 2 * self.margin, self.height - 2 * self.margin), 10, 10
        )

        title_rect = QRect(self.margin, self.margin, self.width - 2 * self.margin, 30)

        painter.setBrush(QBrush(QColor(self.view.theme.value.primary)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(title_rect, 10, 10)
        painter.drawRect(QRect(title_rect.x(), title_rect.y() + 10, title_rect.width(), title_rect.height() - 10))

        painter.setPen(QPen(QColor(self.view.theme.value.foreground)))
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, self.title)

    def mousePressEvent(self, event):  # noqa: N802
        grip_rect = QRectF(
            self.width - self.resize_grip_size,
            self.height - self.resize_grip_size,
            self.resize_grip_size,
            self.resize_grip_size,
        )
        self.start_pos = self.pos()
        self.start_span = self.span_x, self.span_y
        if grip_rect.contains(event.pos()):
            self.resizing = True
            self.start_resize_pos = event.pos()
            self.start_width = self.width
            self.start_height = self.height
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # noqa: N802
        self.setZValue(2)
        if self.resizing:
            delta_x = event.pos().x() - self.start_resize_pos.x()
            delta_y = event.pos().y() - self.start_resize_pos.y()

            new_width = max(self.min_width, self.start_width + delta_x)  # Enforce minimum width
            new_height = max(self.min_height, self.start_height + delta_y)  # Enforce minimum height

            new_span_x = round(new_width / self.grid_size)
            new_span_y = round(new_height / self.grid_size)

            new_width = new_span_x * self.grid_size  # Recalculate width
            new_height = new_span_y * self.grid_size  # Recalculate height

            if new_width != self.width or new_height != self.height:
                self.width = new_width
                self.height = new_height
                self.span_x = new_span_x
                self.span_y = new_span_y
                self.prepareGeometryChange()
            self.view.update_highlight(self.pos(), self, new_span_x, new_span_y)
            event.accept()
        else:
            self.view.update_highlight(self.pos(), self, self.span_x, self.span_y)
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: N802
        super().mouseReleaseEvent(event)
        self.setZValue(1)
        if self.resizing:
            self.resizing = False
            if self.view.is_valid_drop_position(self.pos(), self, self.span_x, self.span_y):
                self.snap_to_grid()
            else:
                self.setPos(self.start_pos)
                self.set_span(*self.start_span)
        elif self.view.is_valid_drop_position(self.pos(), self, self.span_x, self.span_y):
            self.snap_to_grid()
        else:
            self.setPos(self.start_pos)
        self.view.hide_highlight()

    def hoverEnterEvent(self, event):  # noqa: N802
        self.hovering = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):  # noqa: N802
        self.hovering = False
        self.update()
        super().hoverLeaveEvent(event)

    def set_span(self, x, y):
        self.span_x = x
        self.span_y = y
        self.width = self.grid_size * x
        self.height = self.grid_size * y
        self.update()

    def snap_to_grid(self):
        grid_size = self.grid_size
        new_x = round(self.pos().x() / grid_size) * grid_size
        new_y = round(self.pos().y() / grid_size) * grid_size
        rows, cols = self.view.rows, self.view.cols
        new_x = max(0, min(new_x, (cols - self.span_x) * grid_size))
        new_y = max(0, min(new_y, (rows - self.span_y) * grid_size))
        self.setPos(new_x, new_y)

    def create_context_menu(self):
        menu = QMenu(self.view)
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.delete_self)
        edit_title_action = QAction("Edit Title", self)
        edit_title_action.triggered.connect(self.edit_title)

        menu.addAction(delete_action)
        menu.addAction(edit_title_action)

        return menu

    def contextMenuEvent(self, event):  # noqa: N802
        self.create_context_menu().exec(event.screenPos())

    def edit_title(self):
        new_title, ok = QInputDialog.getText(self.view, "Edit Title", "Enter new title:", text=self.title)
        if ok and new_title:
            self.title = new_title
            self.update()

    @abstractmethod
    def close(self):
        pass

    def delete_self(self):
        self.close()
        self.item_deleted.emit(self)

    @abstractmethod
    def update_data(self, data: dict):
        if self.scene():
            self.scene().update(self.sceneBoundingRect())
