import time
from typing import TYPE_CHECKING
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGraphicsProxyWidget,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QCheckBox,
)
import pyqtgraph as pg

from kevinbotlib.apps.common.settings_rows import Divider
from kevinbotlib.apps.dashboard.helpers import get_structure_text
from kevinbotlib.apps.dashboard.widgets.base import WidgetItem
from kevinbotlib.comm import RedisCommClient

if TYPE_CHECKING:
    from kevinbotlib.apps.dashboard.app import GridGraphicsView


class GraphWidgetSettings(QDialog):
    options_changed = Signal(dict)

    def __init__(self, graph, options: dict | None = None, parent=None):
        super().__init__(parent)
        if not options:
            options = {"min": 0, "max": 100, "auto_scale": True}
        self.options = options

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

        self.button_layout = QHBoxLayout()
        self.button_layout.addStretch()
        self.root_layout.addLayout(self.button_layout)

        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply)
        self.button_layout.addWidget(self.apply_button)

        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.close)
        self.button_layout.addWidget(self.exit_button)

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
        self.min_width = self.grid_size * 4  # Minimum width in pixels
        self.min_height = self.grid_size * 3  # Minimum height in pixels

        self.graph = pg.PlotWidget(axisItems={"bottom": pg.DateAxisItem()})
        self.graph.setBackground(grid.theme.value.item_background)
        self.graph.setMouseTracking(False)
        self.graph.setMouseEnabled(x=False, y=False)
        self.graph.showGrid(x=True, y=True, alpha=0.3)
        self.graph.mouseMoveEvent = lambda _: None
        self.graph.mousePressEvent = lambda _: None
        self.graph.mouseReleaseEvent = lambda _: None
        self.graph.setAntialiasing(False)

        if not self.options.get("auto_scale", True):
            self.graph.setYRange(
                self.options.get("min", 0),
                self.options.get("max", 100)
            )

        self.plot: pg.PlotDataItem = self.graph.plot(
            pen=pg.mkPen(color=grid.theme.value.primary, width=2)
        )

        # Create settings dialog
        self.settings = GraphWidgetSettings(self.graph, self.options, grid)
        self.settings.options_changed.connect(self.options_changed)

        # Create proxy widget to hold the plot
        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(self.graph)

        # Initialize data storage
        self.current_value = 0.0
        self.data_points = []  # Stores (timestamp, value) tuples
        self.max_points = 50  # Maximum number of points to display

        self.update_widget_geometry()

    def update_widget_geometry(self):
        widget_margin = self.margin + 30  # 30 is the title bar height
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
            # Extract numeric value from data
            if isinstance(data, dict) and "value" in data:
                new_value = float(data["value"])
            elif isinstance(data, (int, float)):
                new_value = float(data)
            else:
                text_value = get_structure_text(data)
                try:
                    new_value = float(text_value)
                except (ValueError, TypeError):
                    return

            # Append new data point with current timestamp
            timestamp = time.perf_counter()
            self.data_points.append((timestamp, new_value))

            # Limit the number of points
            if len(self.data_points) > self.max_points:
                self.data_points.pop(0)

            # Update plot data
            x_data = [t for t, _ in self.data_points]
            y_data = [v for _, v in self.data_points]
            self.plot.setData(x_data, y_data)

            # Update X-axis range
            if self.data_points:
                min_t = min(t for t, _ in self.data_points)
                max_t = max(t for t, _ in self.data_points)
                self.graph.setXRange(min_t, max_t, padding=0.05)

            # Update Y-axis range if auto-scaling is enabled
            if self.options.get("auto_scale", True) and self.data_points:
                min_y = min(v for _, v in self.data_points)
                max_y = max(v for _, v in self.data_points)
                # Add small padding to avoid clipping
                padding = (max_y - min_y) * 0.05 if max_y != min_y else 1
                self.graph.setYRange(min_y - padding, max_y + padding, padding=0)

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
        # Update Y-axis range based on new settings
        if not self.options.get("auto_scale", True):
            self.graph.setYRange(
                self.options.get("min", 0),
                self.options.get("max", 100),
                padding=0
            )
        elif self.data_points:
            # Apply auto-scaling if enabled and data exists
            min_y = min(v for _, v in self.data_points)
            max_y = max(v for _, v in self.data_points)
            padding = (max_y - min_y) * 0.05 if max_y != min_y else 1
            self.graph.setYRange(min_y - padding, max_y + padding, padding=0)

    def close(self):
        pass