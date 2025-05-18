import functools
import json
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Thread
from typing import override

import qtawesome as qta
from PySide6.QtCore import (
    QCommandLineOption,
    QCommandLineParser,
    QCoreApplication,
    QItemSelection,
    QModelIndex,
    QObject,
    QPointF,
    QRect,
    QRectF,
    QRegularExpression,
    QSettings,
    QSize,
    Qt,
    QThread,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import QAction, QBrush, QCloseEvent, QColor, QPainter, QPen, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QFrame,
    QGraphicsObject,
    QGraphicsProxyWidget,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QStyleOptionGraphicsItem,
    QTabWidget,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from kevinbotlib.__about__ import __version__
from kevinbotlib.apps.dashboard.data import get_structure_text, raw_to_string
from kevinbotlib.apps.dashboard.grid_theme import Themes as GridThemes
from kevinbotlib.apps.dashboard.json_editor import JsonEditor
from kevinbotlib.apps.dashboard.toast import Notifier, Severity
from kevinbotlib.apps.dashboard.tree import DictTreeModel
from kevinbotlib.apps.dashboard.widgets import Divider
from kevinbotlib.comm import RedisCommClient
from kevinbotlib.logger import Level, Logger, LoggerConfiguration
from kevinbotlib.ui.theme import Theme, ThemeStyle


class LatencyWorker(QObject):
    get_latency = Signal()
    latency = Signal(float)

    def __init__(self, client: RedisCommClient):
        super().__init__()
        self.client = client
        self.get_latency.connect(self.get)

    @Slot()
    def get(self):
        latency = self.client.get_latency()
        self.latency.emit(latency)


class WidgetItem(QGraphicsObject):
    item_deleted = Signal(object)

    def __init__(self, title: str, key: str, grid: "GridGraphicsView", span_x=1, span_y=1, data=None):
        if data is None:
            data = {}
        super().__init__()

        self.info = data
        self.kind = "base"

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

    @override
    def mousePressEvent(self, event):
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

    @override
    def mouseMoveEvent(self, event):
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

    @override
    def mouseReleaseEvent(self, event):
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

    @override
    def hoverEnterEvent(self, event):
        self.hovering = True
        self.update()
        super().hoverEnterEvent(event)

    @override
    def hoverLeaveEvent(self, event):
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

    @override
    def contextMenuEvent(self, event):
        menu = QMenu(self.view)
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.delete_self)
        menu.addAction(delete_action)

        menu.exec(event.screenPos())

    def delete_self(self):
        self.item_deleted.emit(self)

    def update_data(self, data: dict):
        pass


class LabelWidgetItem(WidgetItem):
    def __init__(self, title: str, key: str, grid: "GridGraphicsView", span_x=1, span_y=1, data: dict | None = None):
        super().__init__(title, key, grid, span_x, span_y, data)
        self.kind = "text"

        self.label = QLabel(get_structure_text(data))
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("background: transparent;")

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


def determine_widget_types(_did: str):
    return {"Basic Text": LabelWidgetItem}


class GridGraphicsView(QGraphicsView):
    def __init__(self, parent=None, grid_size: int = 48, rows=10, cols=10, theme: GridThemes = GridThemes.Dark):
        super().__init__(parent)
        self.grid_size = grid_size
        self.rows, self.cols = rows, cols
        self.theme = theme

        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
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
                    "info": item.info,
                    "kind": item.kind,
                    "title": item.title,
                    "key": item.key,
                }
                widgets.append(widget_info)
        return widgets

    def get_items(self) -> list[WidgetItem]:
        return [item for item in self.view.scene().items() if isinstance(item, WidgetItem)]

    def load(self, item_loader: Callable[[dict], WidgetItem], items: list[dict]):
        for item in items:
            widget_item = item_loader(item)
            self.add_to_pos(widget_item, item["pos"][0], item["pos"][1])


class WidgetPalette(QWidget):
    def __init__(self, graphics_view, client: RedisCommClient, parent=None):
        super().__init__(parent)

        self.client = client

        self.graphics_view = graphics_view
        self.controller = WidgetGridController(self.graphics_view)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tree = QTreeView()
        self.tree.setHeaderHidden(True)
        layout.addWidget(self.tree, 2)

        self.model = DictTreeModel({})
        self.tree.setModel(self.model)
        self.tree.selectionChanged = self._tree_select

        self.panel = TopicStatusPanel(self.client)
        self.panel.added.connect(self.add_widget)
        layout.addWidget(self.panel, 1)

    def _tree_select(self, selected: QItemSelection, _: QItemSelection):
        self.panel.set_data(selected.indexes()[0].data(Qt.ItemDataRole.UserRole))

    def add_widget(self, widget_info: tuple[type[WidgetItem], str, dict]):
        self.controller.add(
            widget_info[0](widget_info[1], self.panel.current_key, self.graphics_view, data=widget_info[2])
        )

    def remove_widget(self, widget):
        self.graphics_view.scene().removeItem(widget)


class SettingsWindow(QDialog):
    on_applied = Signal()

    def __init__(self, parent, settings: QSettings):
        super().__init__(parent=parent)

        self.settings = settings

        self.root_layout = QVBoxLayout()
        self.setLayout(self.root_layout)

        self.form = QFormLayout()
        self.root_layout.addLayout(self.form)

        self.form.addRow(Divider("Theme"))

        self.theme = UiColorSettingsSwitcher(settings, "theme", parent)
        self.form.addRow("Theme", self.theme)

        self.form.addRow(Divider("Grid"))

        self.grid_size = QSpinBox(minimum=8, maximum=256, singleStep=2, value=self.settings.value("grid", 48, int))  # type: ignore
        self.form.addRow("Grid Size", self.grid_size)

        self.grid_rows = QSpinBox(minimum=1, maximum=256, singleStep=2, value=self.settings.value("rows", 10, int))  # type: ignore
        self.form.addRow("Grid Rows", self.grid_rows)

        self.grid_cols = QSpinBox(minimum=1, maximum=256, singleStep=2, value=self.settings.value("cols", 10, int))  # type: ignore
        self.form.addRow("Grid Columns", self.grid_cols)

        self.form.addRow(Divider("Network"))

        self.net_ip = QLineEdit(self.settings.value("ip", "10.0.0.2", str), placeholderText="***.***.***.***")  # type: ignore
        ip_range = "(?:[0-1]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])"
        ip_regex = QRegularExpression("^" + ip_range + "\\." + ip_range + "\\." + ip_range + "\\." + ip_range + "$")
        ip_validator = QRegularExpressionValidator(ip_regex)
        self.net_ip.setValidator(ip_validator)
        self.form.addRow("IP Address", self.net_ip)

        self.net_port = QSpinBox(minimum=1024, maximum=65535, value=self.settings.value("port", 8765, int))  # type: ignore
        self.form.addRow("Port", self.net_port)

        self.button_layout = QHBoxLayout()
        self.button_layout.addStretch()
        self.root_layout.addLayout(self.button_layout)

        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply)
        self.button_layout.addWidget(self.apply_button)

    def apply(self):
        self.on_applied.emit()


class UiColorSettingsSwitcher(QFrame):
    def __init__(
        self,
        settings: QSettings,
        key: str,
        main_window: "Application",
    ):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)

        self.settings = settings
        self.key = key
        self.main_window = main_window

        root_layout = QHBoxLayout()
        self.setLayout(root_layout)

        self.dark_mode = QRadioButton("Dark")
        self.light_mode = QRadioButton("Light")
        self.system_mode = QRadioButton("System")

        root_layout.addWidget(self.dark_mode)
        root_layout.addWidget(self.light_mode)
        root_layout.addWidget(self.system_mode)

        # Load saved theme setting
        current_theme = self.settings.value(self.key, "Dark")
        if current_theme == "Dark":
            self.dark_mode.setChecked(True)
        elif current_theme == "Light":
            self.light_mode.setChecked(True)
        else:
            self.system_mode.setChecked(True)

        self.dark_mode.toggled.connect(lambda: self.save_setting("Dark"))
        self.light_mode.toggled.connect(lambda: self.save_setting("Light"))
        self.system_mode.toggled.connect(lambda: self.save_setting("System"))

    def save_setting(self, value: str):
        self.settings.setValue(self.key, value)
        self.settings.sync()
        self.main_window.apply_theme()


class TopicStatusPanel(QStackedWidget):
    added = Signal(tuple)

    def __init__(self, client: RedisCommClient):
        super().__init__()
        self.setFrameShape(QFrame.Shape.Panel)

        self.client = client
        self.current_key: str | None = None

        # No data widget
        no_data_label = QLabel("Select a topic for more info", alignment=Qt.AlignmentFlag.AlignCenter)
        no_data_label.setContentsMargins(16, 16, 16, 16)
        self.addWidget(no_data_label)

        # Main data widget with tabs
        data_widget = QWidget()
        self.addWidget(data_widget)

        data_layout = QVBoxLayout()
        data_widget.setLayout(data_layout)

        self.data_topic = QLabel()
        self.data_topic.setStyleSheet("font-size: 18px;")
        data_layout.addWidget(self.data_topic)

        data_layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        # Tab widget for switching views
        self.tab_widget = QTabWidget()
        data_layout.addWidget(self.tab_widget)

        # Data view (existing content)
        data_view = QWidget()
        data_view_layout = QVBoxLayout()
        data_view.setLayout(data_view_layout)

        data_view_layout.addStretch()

        self.data_type = QLabel("Data Type: Unknown")
        data_view_layout.addWidget(self.data_type)

        self.data_known = QLabel("Data Compatible: Unknown")
        data_view_layout.addWidget(self.data_known)

        self.value = QLabel("Value: Dashboard Error")
        data_view_layout.addWidget(self.value)

        data_view_layout.addStretch()

        self.add_layout = QHBoxLayout()
        data_view_layout.addLayout(self.add_layout)

        data_view_layout.addStretch()

        self.tab_widget.addTab(data_view, "Data View")

        # Raw view
        raw_view = QWidget()
        raw_view_layout = QVBoxLayout()
        raw_view.setLayout(raw_view_layout)

        self.raw_text = JsonEditor()
        self.raw_text.setReadOnly(True)
        self.raw_text.setPlaceholderText("Raw data will appear here")
        raw_view_layout.addWidget(self.raw_text)

        self.tab_widget.addTab(raw_view, "Raw View")

    def set_data(self, data: str | None):
        if not data:
            self.setCurrentIndex(0)
            self.data_topic.setText("")
            self.data_type.setText("Data Type: Unknown")
            self.data_known.setText("Data Compatible: Unknown")
            self.value.setText("Value: Dashboard Error")
            self.raw_text.setText("")
            return

        self.setCurrentIndex(1)

        self.data_topic.setText(data)
        self.current_key = data
        raw = self.client.get_raw(data)
        self.data_type.setText(f"Data Type: {raw['did'] if raw else 'Unknown'}")
        self.data_known.setText(f"Data Compatible: {raw['did'] in self.client.SENDABLE_TYPES}")
        self.value.setText(f"Value: {raw_to_string(raw)}")
        # Update raw view with formatted raw data
        raw_content = json.dumps(raw, indent=2) if raw else "No raw data available"
        if raw_content != self.raw_text.document().toPlainText():
            self.raw_text.setText(raw_content)

        for item in reversed(range(self.add_layout.count())):
            litem = self.add_layout.itemAt(item)
            widget = litem.widget()
            self.add_layout.removeItem(litem)
            widget.setParent(None)

        for name, wtype in determine_widget_types(raw["did"]).items():
            button = QToolButton()
            button.setText(f"Add {name}")
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setIcon(qta.icon("mdi6.card-plus"))
            button.pressed.connect(functools.partial(self.added.emit, (wtype, data, raw)))
            self.add_layout.addWidget(button)


class PollingWorker(QObject):
    result_ready = Signal(dict, list, list)

    def __init__(self, client, model, tree, get_index_path, controller: WidgetGridController):
        super().__init__()
        self.client = client
        self.model = model
        self.tree = tree
        self.controller = controller
        self.get_index_path = get_index_path

    @Slot()
    def run(self):
        if not self.client.is_connected():
            return

        data_store = self.client.get_keys()
        data = {}
        raw_data = {}

        for key, value in [(key, self.client.get_raw(key)) for key in data_store]:
            raw_data[key] = value
            if not value:
                continue

            if "struct" in value and "dashboard" in value["struct"]:
                structured = {}
                for viewable in value["struct"]["dashboard"]:
                    display = ""
                    if "element" in viewable:
                        raw = value[viewable["element"]]
                        if "format" in viewable:
                            fmt = viewable["format"]
                            if fmt == "percent":
                                display = f"{raw * 100:.2f}%"
                            elif fmt == "degrees":
                                display = f"{raw}°"
                            elif fmt == "radians":
                                display = f"{raw} rad"
                            elif fmt.startswith("limit:"):
                                limit = int(fmt.split(":")[1])
                                display = raw[:limit]
                            else:
                                display = raw

                    structured[viewable["element"]] = display
                data[key] = structured

        def to_hierarchical_dict(flat_dict: dict):
            hierarchical_dict = {}
            for key, value in flat_dict.items():
                parts = key.split("/")
                d = hierarchical_dict
                for part in parts[:-1]:
                    d = d.setdefault(part, {})
                d[parts[-1]] = {"items": value, "key": key}
            return hierarchical_dict

        hierarchical = to_hierarchical_dict(data)

        expanded_indexes = []

        def store_expansion(parent):
            for row in range(self.model.rowCount(parent)):
                index = self.model.index(row, 0, parent)
                if self.tree.isExpanded(index):
                    expanded_indexes.append((self.get_index_path(index), True))
                store_expansion(index)

        store_expansion(QModelIndex())

        selected_paths = [
            self.get_index_path(index) for index in self.tree.selectionModel().selectedIndexes() if index.column() == 0
        ]

        for widget in self.controller.get_items():
            if widget.key in data_store:
                widget.update_data(raw_data[widget.key])

        self.result_ready.emit(hierarchical, expanded_indexes, selected_paths)


class Application(QMainWindow):
    def __init__(self, _app: QApplication, logger: Logger):
        super().__init__()
        self.setWindowTitle("KevinbotLib Dashboard")

        self.settings = QSettings("kevinbotlib", "dashboard")

        self.logger = logger

        self.client = RedisCommClient(
            host=self.settings.value("ip", "10.0.0.2", str),  # type: ignore
            port=self.settings.value("port", 6379, int),  # type: ignore
            on_disconnect=self.on_disconnect,
            on_connect=self.on_connect,
        )

        self.notifier = Notifier(self)

        self.menu = self.menuBar()
        self.menu.setNativeMenuBar(False)

        self.file_menu = self.menu.addMenu("&File")

        self.save_action = self.file_menu.addAction("Save Layout", self.save_slot)
        self.save_action.setShortcut("Ctrl+S")

        self.quit_action = self.file_menu.addAction("Quit", self.close)
        self.quit_action.setShortcut("Alt+F4")

        self.edit_menu = self.menu.addMenu("&Edit")

        self.settings_action = self.edit_menu.addAction("Settings", self.open_settings)
        self.settings_action.setShortcut("Ctrl+,")

        self.status = self.statusBar()

        self.connection_status = QLabel("Robot Disconnected")
        self.status.addWidget(self.connection_status)

        self.ip_status = QLabel(str(self.settings.value("ip", "10.0.0.2", str)), alignment=Qt.AlignmentFlag.AlignCenter)
        self.status.addWidget(self.ip_status, 1)

        self.latency_status = QLabel("Latency: 0.00")
        self.status.addPermanentWidget(self.latency_status)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        layout = QHBoxLayout(main_widget)

        self.graphics_view = GridGraphicsView(
            grid_size=self.settings.value("grid", 48, int),  # type: ignore
            rows=self.settings.value("rows", 10, int),  # type: ignore
            cols=self.settings.value("cols", 10, int),  # type: ignore
            theme=GridThemes.Dark,
        )
        palette = WidgetPalette(self.graphics_view, self.client)
        self.model = palette.model
        self.tree = palette.tree

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.graphics_view)
        splitter.addWidget(palette)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

        self.latency_thread = QThread(self)
        self.latency_worker = LatencyWorker(self.client)
        self.latency_worker.moveToThread(self.latency_thread)
        self.latency_thread.start()
        self.latency_worker.latency.connect(self.update_latency)

        self.latency_timer = QTimer()
        self.latency_timer.setInterval(1000)
        self.latency_timer.timeout.connect(self.latency_worker.get_latency.emit)
        self.latency_timer.start()

        self.controller = WidgetGridController(self.graphics_view)
        self.controller.load(self.item_loader, self.settings.value("layout", [], type=list))  # type: ignore

        self.tree_worker_thread = QThread(self)
        self.tree_worker = PollingWorker(
            client=self.client,
            model=self.model,
            tree=self.tree,
            get_index_path=self.get_index_path,
            controller=self.controller,
        )
        self.tree_worker.moveToThread(self.tree_worker_thread)
        self.tree_worker.result_ready.connect(self._apply_tree_update)
        self.tree_worker_thread.start()

        self.update_timer = QTimer()
        self.update_timer.setInterval(100)
        self.update_timer.timeout.connect(self.tree_worker.run)
        self.update_timer.start()

        self.settings_window = SettingsWindow(self, self.settings)
        self.settings_window.on_applied.connect(self.refresh_settings)

        self.theme = Theme(ThemeStyle.System)
        self.apply_theme()

        self.connection_governor_thread = Thread(
            target=self.connection_governor, daemon=True, name="KevinbotLib.Dashboard.Connection.Governor"
        )
        self.connection_governor_thread.start()

    def connection_governor(self):
        while True:
            if not self.client.is_connected():
                self.client.connect()
            time.sleep(2)

    def apply_theme(self):
        theme_name = self.settings.value("theme", "Dark")
        if theme_name == "Dark":
            self.theme.set_style(ThemeStyle.Dark)
            self.graphics_view.set_theme(GridThemes.Dark)
        elif theme_name == "Light":
            self.theme.set_style(ThemeStyle.Light)
            self.graphics_view.set_theme(GridThemes.Light)
        else:
            self.theme.set_style(ThemeStyle.System)
            if self.theme.is_dark():
                self.graphics_view.set_theme(GridThemes.Dark)
            else:
                self.graphics_view.set_theme(GridThemes.Light)
        self.theme.apply(self)

    def update_latency(self, latency: float | None):
        if latency:
            self.latency_status.setText(f"Latency: {latency:.2f}ms")
        else:
            self.latency_status.setText("Latency: --.--ms")

    @Slot(dict, list, list)
    def _apply_tree_update(self, hierarchical_data, expanded_indexes, selected_paths):
        self.model.update_data(hierarchical_data)

        for path, was_expanded in expanded_indexes:
            index = self.get_index_from_path(path)
            if index.isValid() and was_expanded:
                self.tree.setExpanded(index, True)

        selection_model = self.tree.selectionModel()
        selection_model.clear()
        for path in selected_paths:
            index = self.get_index_from_path(path)
            if index.isValid():
                selection_model.select(index, selection_model.SelectionFlag.Select | selection_model.SelectionFlag.Rows)

    def update_tree(self):
        self.tree_worker.run()

    def get_selection_paths(self):
        return [
            self.get_index_path(index) for index in self.tree.selectionModel().selectedIndexes() if index.column() == 0
        ]

    def restore_selection(self, paths):
        selection_model = self.tree.selectionModel()
        selection_model.clear()
        for path in paths:
            index = self.get_index_from_path(path)
            if index.isValid():
                selection_model.select(index, selection_model.SelectionFlag.Select | selection_model.SelectionFlag.Rows)

    def get_index_path(self, index):
        path = []
        while index.isValid():
            path.append(index.row())
            index = self.model.parent(index)
        return tuple(reversed(path))

    def get_index_from_path(self, path):
        index = QModelIndex()
        for row in path:
            index = self.model.index(row, 0, index)
        return index

    def on_connect(self):
        self.connection_status.setText("Robot Connected")
        self.update_tree()

    def on_disconnect(self):
        self.connection_status.setText("Robot Disconnected")

    def refresh_settings(self):
        self.settings.setValue("ip", self.settings_window.net_ip.text())
        self.settings.setValue("port", self.settings_window.net_port.value())
        if self.client.host != self.settings.value("ip", "10.0.0.2", str):  # type: ignore
            self.client.host = self.settings.value("ip", "10.0.0.2", str)  # type: ignore
        if self.client.port != self.settings.value("port", 6379, int):  # type: ignore
            self.client.port = self.settings.value("port", 6379, int)  # type: ignore

        self.ip_status.setText(str(self.settings.value("ip", "10.0.0.2", str)))

        self.settings.setValue("grid", self.settings_window.grid_size.value())
        self.settings.setValue("rows", self.settings_window.grid_rows.value())
        self.settings.setValue("cols", self.settings_window.grid_cols.value())

        self.graphics_view.set_grid_size(self.settings.value("grid", 48, int))  # type: ignore
        if not self.graphics_view.resize_grid(
            self.settings.value("rows", 10, int), self.settings.value("cols", 10, int)
        ):  # type: ignore
            QMessageBox.critical(self.settings_window, "Error", "Cannot resize grid to the specified dimensions.")
            self.settings.setValue("rows", self.graphics_view.rows)
            self.settings.setValue("cols", self.graphics_view.cols)

    def item_loader(self, item: dict) -> WidgetItem:
        kind = item["kind"]
        title = item["title"]
        span_x = item["span_x"]
        span_y = item["span_y"]
        data = item["info"]
        key = item["key"] if "key" in item else item["title"]
        match kind:
            case "base":
                return WidgetItem(title, key, self.graphics_view, span_x, span_y, data)
            case "text":
                return LabelWidgetItem(title, key, self.graphics_view, span_x, span_y, data)

        return WidgetItem(title, key, self.graphics_view, span_x, span_y)

    @override
    def closeEvent(self, event: QCloseEvent):
        reply = QMessageBox.question(
            self,
            "Save Layout",
            "Do you want to save the current layout before exiting?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.save_slot()
            self.tree_worker_thread.quit()
            self.latency_thread.quit()
            event.accept()
        elif reply == QMessageBox.StandardButton.No:
            self.tree_worker_thread.quit()
            self.latency_thread.quit()
            event.accept()
        else:
            event.ignore()

    def save_slot(self):
        self.settings.setValue("layout", self.controller.get_widgets())
        self.notifier.toast("Layout Saved", "Layout saved successfully", severity=Severity.Success)

    def open_settings(self):
        self.settings_window.show()


@dataclass
class DashboardApplicationStartupArguments:
    verbose: bool = False
    trace: bool = True


class DashboardApplicationRunner:
    def __init__(self, args: DashboardApplicationStartupArguments | None = None):
        self.logger = Logger()
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("KevinbotLib Dashboard")
        self.app.setApplicationVersion(__version__)
        self.app.setStyle("Fusion")  # can solve some platform-specific issues

        self.configure_logger(args)
        self.window = None

    def configure_logger(self, args: DashboardApplicationStartupArguments | None):
        if args is None:
            parser = QCommandLineParser()
            parser.addHelpOption()
            parser.addVersionOption()
            parser.addOption(QCommandLineOption(["V", "verbose"], "Enable verbose (DEBUG) logging"))
            parser.addOption(
                QCommandLineOption(
                    ["T", "trace"],
                    QCoreApplication.translate("main", "Enable tracing (TRACE logging)"),
                )
            )
            parser.process(self.app)

            log_level = Level.INFO
            if parser.isSet("verbose"):
                log_level = Level.DEBUG
            elif parser.isSet("trace"):
                log_level = Level.TRACE
        else:
            log_level = Level.INFO
            if args.verbose:
                log_level = Level.DEBUG
            elif args.trace:
                log_level = Level.TRACE

        self.logger.configure(LoggerConfiguration(level=log_level))

    def run(self):
        # kevinbotlib.apps.dashboard.resources_rc.qInitResources()
        self.window = Application(self.app, self.logger)
        self.window.show()
        sys.exit(self.app.exec())


def execute(args: DashboardApplicationStartupArguments | None):
    runner = DashboardApplicationRunner(args)
    runner.run()


if __name__ == "__main__":
    execute(None)
