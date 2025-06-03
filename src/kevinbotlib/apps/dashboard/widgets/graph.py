from enum import Enum
from typing import TYPE_CHECKING, Any

import pyqtgraph
import superqt
from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGraphicsProxyWidget,
    QHBoxLayout,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from kevinbotlib.apps.common.settings_rows import Divider
from kevinbotlib.apps.dashboard.helpers import get_structure_text
from kevinbotlib.apps.dashboard.widgets._pglive.sources.data_connector import DataConnector
from kevinbotlib.apps.dashboard.widgets._pglive.sources.live_plot import LiveLinePlot
from kevinbotlib.apps.dashboard.widgets._pglive.sources.live_plot_widget import LivePlotWidget
from kevinbotlib.apps.dashboard.widgets.base import WidgetItem
from kevinbotlib.comm import RedisCommClient

if TYPE_CHECKING:
    from kevinbotlib.apps.dashboard.app import GridGraphicsView


class GraphColors(Enum):
    Red = "#b44646"
    Green = "#46b482"
    Blue = "#4682b4"
    White = "#e4e4e4"
    Black = "060606"
    Yellow = "#e4e446"
    Magenta = "#b446b4"


class GraphWidgetSettings(QDialog):
    options_changed = Signal(dict)

    def __init__(self, _graph, options: dict[str, Any] | None = None, parent=None):
        super().__init__(parent)
        if not options:
            options = {}
        self.options: dict[str, Any] = options

        self.setWindowTitle("Graph Settings")
        self.setModal(True)

        self.root_layout = QVBoxLayout()
        self.setLayout(self.root_layout)

        self.form = QFormLayout()
        self.root_layout.addLayout(self.form)

        self.form.addRow(Divider("Range"))

        self.auto_scale = QCheckBox()
        self.auto_scale.setChecked(self.options.get("auto_scale", True))
        self.auto_scale.stateChanged.connect(self.set_auto_scale)
        self.form.addRow("Auto Scale Y-Axis", self.auto_scale)

        self.min_value = QDoubleSpinBox()
        self.min_value.setValue(self.options.get("min", 0))
        self.min_value.setRange(-2_147_483_648, 2_147_483_647)
        self.min_value.setDecimals(2)
        self.min_value.setEnabled(not self.options.get("auto_scale", False))
        self.min_value.valueChanged.connect(self.set_min_value)
        self.min_value.setDisabled(self.options.get("auto_scale", True))
        self.form.addRow("Min Value", self.min_value)

        self.max_value = QDoubleSpinBox()
        self.max_value.setValue(self.options.get("max", 100))
        self.max_value.setRange(-2_147_483_648, 2_147_483_647)
        self.max_value.setDecimals(2)
        self.max_value.setEnabled(not self.options.get("auto_scale", False))
        self.max_value.valueChanged.connect(self.set_max_value)
        self.max_value.setDisabled(self.options.get("auto_scale", True))
        self.form.addRow("Max Value", self.max_value)

        self.form.addRow(Divider("Data"))

        self.points = QSpinBox(minimum=20, maximum=200, value=self.options.get("points", 50))
        self.points.valueChanged.connect(self.set_points)
        self.form.addRow("Data Points", self.points)

        self.interval = QSpinBox(
            minimum=1, maximum=1000, singleStep=25, value=self.options.get("interval", 50), suffix="ms"
        )
        self.interval.valueChanged.connect(self.set_interval)
        self.form.addRow("Point Interval", self.interval)

        self.form.addRow(Divider("Visuals"))

        self.color = superqt.QEnumComboBox()
        self.color.setEnumClass(GraphColors)
        self.color.setCurrentEnum(GraphColors(self.options.get("color", "#4682b4")))
        self.color.currentEnumChanged.connect(self.set_color)
        self.form.addRow("Line Color", self.color)

        self.width = QSpinBox(minimum=1, maximum=6, value=self.options.get("width", 2))
        self.width.valueChanged.connect(self.set_width)
        self.form.addRow("Line Width", self.width)

        self.button_layout = QHBoxLayout()
        self.button_layout.addStretch()
        self.root_layout.addLayout(self.button_layout)

        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply)
        self.button_layout.addWidget(self.apply_button)

        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.close)
        self.button_layout.addWidget(self.exit_button)

    def set_color(self, color: GraphColors):
        self.options["color"] = color.value

    def set_width(self, width: int):
        self.options["width"] = width

    def set_points(self, points: int):
        self.options["points"] = points

    def set_interval(self, interval: int):
        self.options["interval"] = interval

    def set_auto_scale(self, state: int):
        self.options["auto_scale"] = bool(state)
        self.min_value.setEnabled(not self.options["auto_scale"])
        self.max_value.setEnabled(not self.options["auto_scale"])

    def set_min_value(self, value: float):
        self.options["min"] = value

    def set_max_value(self, value: float):
        self.options["max"] = value

    def apply(self):
        self.options_changed.emit(self.options)


class GraphWidgetItem(WidgetItem):
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
        self.kind = "graph"
        self.min_width = self.grid_size * 4
        self.min_height = self.grid_size * 3

        self.graph = LivePlotWidget(
            background=grid.theme.value.item_background,
        )
        self.graph.setMouseTracking(False)
        self.graph.setMouseEnabled(x=False, y=False)
        self.graph.showGrid(x=True, y=True, alpha=0.3)
        self.graph.mouseMoveEvent = lambda _: None
        self.graph.mousePressEvent = lambda _: None
        self.graph.mouseReleaseEvent = lambda _: None
        self.graph.wheelEvent = lambda _: None
        self.graph.setAntialiasing(False)

        self.plot = LiveLinePlot(
            pen=pyqtgraph.mkPen(
                GraphColors(self.options.get("color", "#4682b4")).value, width=self.options.get("width", 2)
            )
        )
        self.graph.addItem(self.plot)

        self.settings = GraphWidgetSettings(self.graph, self.options, grid)
        self.settings.options_changed.connect(self.options_changed)

        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(self.graph)

        self.current_value = 0.0
        self.max_points = self.options.get("points", 50)
        self.connector = DataConnector(self.plot, max_points=self.max_points)

        self.timer = QTimer()
        self.timer.setInterval(self.options.get("interval", 50))
        self.timer.timeout.connect(self.worker_update)
        self.timer.start()

        self.update_widget_geometry()

    def update_widget_geometry(self):
        widget_margin = self.margin + 30
        widget_rect = (
            self.margin + 4,
            widget_margin + 4,
            self.width - 2 * self.margin - 8,
            self.height - widget_margin - self.margin - 8,
        )
        self.proxy.setGeometry(*widget_rect)

    def set_span(self, x, y):
        super().set_span(x, y)
        self.update_widget_geometry()

    def prepareGeometryChange(self):  # noqa: N802
        super().prepareGeometryChange()
        self.update_widget_geometry()

    def update_data(self, data: dict):
        super().update_data(data)
        try:
            if isinstance(data, dict) and "value" in data:
                self.current_value = float(data["value"])
            elif isinstance(data, int | float):
                self.current_value = float(data)
            else:
                text_value = get_structure_text(data)
                self.current_value = float(text_value)
        except (ValueError, TypeError):
            pass

    def create_context_menu(self):
        menu = super().create_context_menu()
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.settings.show)
        menu.addAction(settings_action)
        return menu

    def options_changed(self, options: dict):
        self.options = options
        self.timer.setInterval(self.options.get("interval", 50))
        self.max_points = self.options.get("points", 50)
        self.plot.setPen(
            color=GraphColors(self.options.get("color", "#4682b4")).value,
            width=self.options.get("width", 2),
        )
        self.connector.max_points = self.max_points
        if not self.options.get("auto_scale", True):
            self.graph.setYRange(self.options.get("min", 0), self.options.get("max", 100))
        else:
            self.graph.enableAutoRange(axis="y", enable=True)

    def worker_update(self):
        self.connector.cb_append_data_point(self.current_value)

        if not self.options.get("auto_scale", True):
            self.graph.setYRange(self.options.get("min", 0), self.options.get("max", 100))

    def close(self):
        self.timer.stop()
