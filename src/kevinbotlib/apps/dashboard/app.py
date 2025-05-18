import functools
import json
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from queue import Queue
from threading import Thread
from typing import override

import ansi2html
import qtawesome as qta
from PySide6.QtCore import (
    QCommandLineOption,
    QCommandLineParser,
    QCoreApplication,
    QItemSelection,
    QModelIndex,
    QObject,
    QPointF,
    QPropertyAnimation,
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
from PySide6.QtGui import (
    QBrush,
    QCloseEvent,
    QColor,
    QPainter,
    QPen,
    QRegularExpressionValidator,
    QTextOption,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QFrame,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from kevinbotlib.__about__ import __version__
from kevinbotlib.apps.dashboard.grid_theme import Themes as GridThemes
from kevinbotlib.apps.dashboard.helpers import get_structure_text
from kevinbotlib.apps.dashboard.json_editor import JsonEditor
from kevinbotlib.apps.dashboard.qwidgets import Divider
from kevinbotlib.apps.dashboard.toast import NotificationWidget, Notifier, Severity
from kevinbotlib.apps.dashboard.tree import DictTreeModel
from kevinbotlib.apps.dashboard.widgets.base import WidgetItem
from kevinbotlib.apps.dashboard.widgets.biglabel import BigLabelWidgetItem
from kevinbotlib.apps.dashboard.widgets.label import LabelWidgetItem
from kevinbotlib.apps.dashboard.widgets.mjpeg import MjpegCameraStreamWidgetItem
from kevinbotlib.apps.dashboard.widgets.textedit import TextEditWidgetItem
from kevinbotlib.comm import RedisCommClient
from kevinbotlib.logger import Level, Logger, LoggerConfiguration
from kevinbotlib.ui.theme import Theme, ThemeStyle
from kevinbotlib.vision import VisionCommUtils


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


def determine_widget_types(did: str):
    match did:
        case "kevinbotlib.dtype.int":
            return {"Basic Text": LabelWidgetItem, "Text Edit": TextEditWidgetItem, "Big Text": BigLabelWidgetItem}
        case "kevinbotlib.dtype.float":
            return {"Basic Text": LabelWidgetItem, "Text Edit": TextEditWidgetItem, "Big Text": BigLabelWidgetItem}
        case "kevinbotlib.dtype.str":
            return {"Basic Text": LabelWidgetItem, "Text Edit": TextEditWidgetItem, "Big Text": BigLabelWidgetItem}
        case "kevinbotlib.dtype.bool":
            return {"Basic Text": LabelWidgetItem, "Big Text": BigLabelWidgetItem}
        case "kevinbotlib.dtype.list.any":
            return {"Basic Text": LabelWidgetItem, "Big Text": BigLabelWidgetItem}
        case "kevinbotlib.dtype.dict":
            return {"Basic Text": LabelWidgetItem, "Big Text": BigLabelWidgetItem}
        case "kevinbotlib.dtype.bin":
            return {"Basic Text": LabelWidgetItem}
        case "kevinbotlib.vision.dtype.mjpeg":
            return {"MJPEG Stream": MjpegCameraStreamWidgetItem}
    return {}


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
            widget_info[0](
                widget_info[1].split("/")[-1],
                self.panel.current_key if self.panel.current_key else "",
                {},
                self.graphics_view,
                1,
                1,
                widget_info[2],
                self.client,
            )
        )

    def remove_widget(self, widget):
        self.graphics_view.scene().removeItem(widget)


class SettingsWindow(QDialog):
    on_applied = Signal()

    def __init__(self, parent: "Application", settings: QSettings):
        super().__init__(parent=parent)

        self.settings = settings

        self.root_layout = QVBoxLayout()
        self.setLayout(self.root_layout)

        self.form = QFormLayout()
        self.root_layout.addLayout(self.form)

        self.form.addRow(Divider("Theme"))

        self.form.addRow(
            NotificationWidget(
                "Warning", "A restart is required to fully apply the theme", Severity.Warning.value, 0, bg=False
            )
        )

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

        self.form.addRow(Divider("Polling"))

        self.poll_rate = QSpinBox(
            minimum=100,
            maximum=2500,
            singleStep=50,
            value=self.settings.value("rate", 200, int),
            suffix="ms",  # type: ignore
        )
        self.form.addRow("Polling Rate", self.poll_rate)

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
        self.raw_data = {}
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
        self.value.setWordWrap(True)
        self.value.setMaximumWidth(1024)
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
        raw = self.raw_data[data] if data in self.raw_data else self.client.get_raw(data)
        if not raw:
            return
        self.data_type.setText(f"Data Type: {raw['did'] if raw else 'Unknown'}")
        self.data_known.setText(f"Data Compatible: {raw['did'] in self.client.SENDABLE_TYPES}")
        self.value.setText(f"Value: {get_structure_text(raw)}")
        # Update raw view with formatted raw data
        raw_content = json.dumps(raw, indent=2) if raw else "No raw data available"
        if self.tab_widget.currentIndex() == 1:
            if raw_content != self.raw_text.document().toPlainText():
                self.raw_text.setText(raw_content)
        elif self.raw_text.toPlainText() != "Raw data will appear here":
            self.raw_text.setText("Raw data will appear here")

        for item in reversed(range(self.add_layout.count())):
            litem = self.add_layout.itemAt(item)
            widget = litem.widget()
            self.add_layout.removeItem(litem)
            widget.setParent(None)

        wt = determine_widget_types(raw["did"])
        if not wt:
            return

        for name, wtype in wt.items():
            button = QToolButton()
            button.setText(f"Add {name}")
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setIcon(qta.icon("mdi6.card-plus"))
            button.pressed.connect(functools.partial(self.added.emit, (wtype, data, raw)))
            self.add_layout.addWidget(button)


class PollingWorker(QObject):
    result_ready = Signal(dict, list, list, dict)

    def __init__(self, client: RedisCommClient, model, tree, get_index_path, controller: WidgetGridController):
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
        raw_data = self.client.get_all_raw()
        if raw_data is None:
            return
        for key in data_store:
            value = raw_data.get(key)
            raw_data[key] = value
            if not value:
                continue

            if "struct" in value and "dashboard" in value["struct"]:
                structured = {}
                for viewable in value["struct"]["dashboard"]:
                    display = ""
                    if "element" in viewable:
                        raw = value.get(viewable["element"], "")
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
            for k, v in flat_dict.items():
                parts = k.split("/")
                d = hierarchical_dict
                for part in parts[:-1]:
                    d = d.setdefault(part, {})
                d[parts[-1]] = {"items": v, "key": k}
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

        self.result_ready.emit(hierarchical, expanded_indexes, selected_paths, raw_data)


class Application(QMainWindow):
    def __init__(self, app: QApplication, logger: Logger):
        super().__init__()
        self.app = app
        self.setWindowTitle("KevinbotLib Dashboard")

        self.settings = QSettings("kevinbotlib", "dashboard")

        self.logger = logger

        self.theme = Theme(ThemeStyle.System)

        self.graphics_view = GridGraphicsView(
            grid_size=self.settings.value("grid", 48, int),  # type: ignore
            rows=self.settings.value("rows", 10, int),  # type: ignore
            cols=self.settings.value("cols", 10, int),  # type: ignore
            theme=GridThemes.Dark,
        )
        self.apply_theme()

        self.client = RedisCommClient(
            host=self.settings.value("ip", "10.0.0.2", str),  # type: ignore
            port=self.settings.value("port", 6379, int),  # type: ignore
            on_disconnect=self.on_disconnect,
            on_connect=self.on_connect,
        )
        VisionCommUtils.init_comms_types(self.client)

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

        root_layout = QVBoxLayout(main_widget)

        main_layout = QHBoxLayout()
        root_layout.addLayout(main_layout, 999)
        self.widget_palette = WidgetPalette(self.graphics_view, self.client)
        self.model = self.widget_palette.model
        self.tree = self.widget_palette.tree

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.graphics_view)
        splitter.addWidget(self.widget_palette)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

        self.log_queue: Queue[str] = Queue(1000)
        self.logger.add_hook_ansi(self.log_hook)

        self.log_timer = QTimer()
        self.log_timer.setInterval(250)
        self.log_timer.timeout.connect(self.update_logs)
        self.log_timer.start()

        self.log_widget = QWidget()
        self.log_widget.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self.log_widget)

        log_layout = QVBoxLayout(self.log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0)

        self.log_view = QTextEdit(placeholderText="No logs yet")
        self.log_view.setReadOnly(True)
        self.log_view.setWordWrapMode(QTextOption.WrapMode.NoWrap)
        self.log_view.document().setMaximumBlockCount(100)
        log_layout.addWidget(self.log_view)

        log_collapse = QToolButton()
        log_collapse.setText("Logs")
        log_collapse.setStyleSheet("padding: 2px;")
        log_collapse.setFixedHeight(24)
        log_collapse.clicked.connect(self.toggle_logs)
        root_layout.addWidget(log_collapse, alignment=Qt.AlignmentFlag.AlignCenter)

        self.log_open_animation = QPropertyAnimation(self.log_widget, b"maximumHeight")  # type: ignore
        self.log_open_animation.setStartValue(0)
        self.log_open_animation.setEndValue(200)
        self.log_open_animation.setDuration(100)

        self.log_close_animation = QPropertyAnimation(self.log_widget, b"maximumHeight")  # type: ignore
        self.log_close_animation.setStartValue(200)
        self.log_close_animation.setEndValue(0)
        self.log_close_animation.setDuration(100)
        self.log_close_animation.start()
        self.log_close_animation.finished.connect(self.log_widget.hide)

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
        self.update_timer.setInterval(self.settings.value("rate", 200, int))  # type: ignore
        self.update_timer.timeout.connect(self.tree_worker.run)
        self.update_timer.start()

        self.settings_window = SettingsWindow(self, self.settings)
        self.settings_window.on_applied.connect(self.refresh_settings)

        self.connection_governor_thread = Thread(
            target=self.connection_governor, daemon=True, name="KevinbotLib.Dashboard.Connection.Governor"
        )
        self.connection_governor_thread.start()

    def log_hook(self, data: str):
        self.log_queue.put(ansi2html.Ansi2HTMLConverter(scheme="osx").convert(data.strip()))

    def update_logs(self):
        while not self.log_queue.empty():
            self.log_view.append(self.log_queue.get())

    def toggle_logs(self):
        if not self.log_widget.isVisible():
            self.log_widget.show()
            self.log_open_animation.start()
        else:
            # noinspection PyAttributeOutsideInit
            self.log_close_animation.start()

    def connection_governor(self):
        while True:
            if not self.client.is_connected():
                self.client.connect()
            time.sleep(2)

    def apply_theme(self):
        theme_name = self.settings.value("theme", "Dark")
        if theme_name == "Dark":
            qta.dark(self.app)
            self.theme.set_style(ThemeStyle.Dark)
            self.graphics_view.set_theme(GridThemes.Dark)
        elif theme_name == "Light":
            qta.light(self.app)
            self.theme.set_style(ThemeStyle.Light)
            self.graphics_view.set_theme(GridThemes.Light)
        else:
            self.theme.set_style(ThemeStyle.System)
            if self.theme.is_dark():
                qta.dark(self.app)
                self.graphics_view.set_theme(GridThemes.Dark)
            else:
                qta.light(self.app)
                self.graphics_view.set_theme(GridThemes.Light)
        self.theme.apply(self)

    def update_latency(self, latency: float | None):
        if latency:
            self.latency_status.setText(f"Latency: {latency:.2f}ms")
        else:
            self.latency_status.setText("Latency: --.--ms")

    @Slot(dict, list, list, dict)
    def _apply_tree_update(self, hierarchical_data, expanded_indexes, selected_paths, raw_data):
        self.model.update_data(hierarchical_data)
        self.widget_palette.panel.raw_data = raw_data

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
            self.settings.value("rows", 10, int),
            self.settings.value("cols", 10, int),  # type: ignore
        ):
            QMessageBox.critical(self.settings_window, "Error", "Cannot resize grid to the specified dimensions.")
            self.settings.setValue("rows", self.graphics_view.rows)
            self.settings.setValue("cols", self.graphics_view.cols)

        self.settings.setValue("rate", self.settings_window.poll_rate.value())
        self.update_timer.setInterval(self.settings.value("rate", 200, int))  # type: ignore

    def item_loader(self, item: dict) -> WidgetItem:
        kind = item["kind"]
        title = item["title"]
        options = item["options"] if "options" in item else {}
        span_x = item["span_x"]
        span_y = item["span_y"]
        data = item["info"]
        key = item["key"] if "key" in item else item["title"]
        match kind:
            case "base":
                return WidgetItem(title, key, options, self.graphics_view, span_x, span_y, data, self.client)
            case "text":
                return LabelWidgetItem(title, key, options, self.graphics_view, span_x, span_y, data, self.client)
            case "bigtext":
                return BigLabelWidgetItem(title, key, options, self.graphics_view, span_x, span_y, data, self.client)
            case "textedit":
                return TextEditWidgetItem(title, key, options, self.graphics_view, span_x, span_y, data, self.client)
            case "cameramjpeg":
                return MjpegCameraStreamWidgetItem(
                    title, key, options, self.graphics_view, span_x, span_y, data, self.client
                )

        return WidgetItem(title, key, options, self.graphics_view, span_x, span_y)

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
