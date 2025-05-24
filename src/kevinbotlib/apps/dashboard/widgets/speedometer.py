from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGraphicsProxyWidget,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
)

from kevinbotlib.apps.common.settings_rows import Divider
from kevinbotlib.apps.dashboard.gradient import GradientEditor
from kevinbotlib.apps.dashboard.helpers import get_structure_text
from kevinbotlib.apps.dashboard.speedometer import Speedometer
from kevinbotlib.apps.dashboard.widgets.base import WidgetItem
from kevinbotlib.comm import RedisCommClient

if TYPE_CHECKING:
    from kevinbotlib.apps.dashboard.app import GridGraphicsView


class SpeedometerWidgetSettings(QDialog):
    options_changed = Signal(dict)

    def __init__(self, speedometer: Speedometer, options: dict | None = None, parent=None):
        super().__init__(parent)
        if not options:
            options = {}
        self.options = options

        self.setWindowTitle("Gauge Settings")
        self.setModal(True)

        self.root_layout = QVBoxLayout()
        self.setLayout(self.root_layout)

        self.form = QFormLayout()
        self.root_layout.addLayout(self.form)

        self.form.addRow(Divider("Value"))

        self.value_display = QCheckBox()
        self.value_display.setChecked(self.options.get("value_display", True))
        self.value_display.checkStateChanged.connect(self.set_value_display)
        self.form.addRow("Display Value", self.value_display)

        self.form.addRow(Divider("Ticks"))

        self.coarse_tick_markers = QCheckBox()
        self.coarse_tick_markers.setChecked(self.options.get("coarse_tick_display", True))
        self.coarse_tick_markers.checkStateChanged.connect(self.set_coarse_tick_value_display)
        self.form.addRow("Display Fine Tick Markers", self.coarse_tick_markers)

        self.fine_tick_markers = QCheckBox()
        self.fine_tick_markers.setChecked(self.options.get("fine_tick_display", True))
        self.fine_tick_markers.checkStateChanged.connect(self.set_fine_tick_value_display)
        self.form.addRow("Display Fine Tick Markers", self.fine_tick_markers)

        self.form.addRow(Divider("Scale"))

        self.scale_display = QCheckBox()
        self.scale_display.setChecked(self.options.get("scale_display", True))
        self.scale_display.checkStateChanged.connect(self.set_scale_display)
        self.form.addRow("Display Scale", self.scale_display)

        self.scale_gradient = GradientEditor(self.options.get("scale", speedometer.scale_polygon_colors))
        self.scale_gradient.gradient_changed.connect(self.set_scale)
        self.form.addRow(self.scale_gradient)

        self.form.addRow(Divider("Range"))

        self.min_value = QDoubleSpinBox()
        self.min_value.setValue(self.options.get("min", 0))
        self.min_value.setRange(-2_147_483_648, 2_147_483_647)
        self.min_value.setDecimals(2)
        self.min_value.valueChanged.connect(self.set_min_value)
        self.form.addRow("Min Value", self.min_value)

        self.max_value = QDoubleSpinBox()
        self.max_value.setValue(self.options.get("max", 100))
        self.max_value.setRange(-2_147_483_648, 2_147_483_647)
        self.max_value.setDecimals(2)
        self.max_value.valueChanged.connect(self.set_max_value)
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

    def set_value_display(self, value: Qt.CheckState):
        self.options["value_display"] = value == Qt.CheckState.Checked

    def set_fine_tick_value_display(self, value: Qt.CheckState):
        self.options["fine_tick_display"] = value == Qt.CheckState.Checked

    def set_coarse_tick_value_display(self, value: Qt.CheckState):
        self.options["coarse_tick_display"] = value == Qt.CheckState.Checked

    def set_scale_display(self, value: Qt.CheckState):
        self.options["scale_display"] = value == Qt.CheckState.Checked

    def set_scale(self, value: list):
        self.options["scale"] = value

    def set_min_value(self, value: float):
        self.options["min"] = value

    def set_max_value(self, value: float):
        self.options["max"] = value

    def apply(self):
        self.options_changed.emit(self.options)


class SpeedometerWidgetItem(WidgetItem):
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
        self.kind = "speedometer"

        # Create the speedometer widget
        self.speedometer = Speedometer()
        self.speedometer.set_scale_value_color(QColor(self.view.theme.value.foreground))
        self.speedometer.set_center_point_color(QColor(self.view.theme.value.foreground))
        self.speedometer.set_display_value_color(QColor(self.view.theme.value.foreground))
        self.speedometer.set_needle_color(QColor(self.view.theme.value.foreground))
        self.speedometer.set_enable_value_text(options.get("value_display", True))
        self.speedometer.set_enable_fine_scaled_marker(options.get("fine_tick_display", True))
        self.speedometer.set_enable_big_scaled_grid(options.get("coarse_tick_display", True))
        self.speedometer.set_enable_scale(options.get("scale_display", True))
        self.speedometer.set_scale_polygon_colors(options.get("scale", self.speedometer.scale_polygon_colors))
        self.speedometer.set_min_value(options.get("min", 0))
        self.speedometer.set_max_value(options.get("max", 100))
        self.speedometer.setStyleSheet("background: transparent;")

        self.settings = SpeedometerWidgetSettings(self.speedometer, self.options, grid)
        self.settings.options_changed.connect(self.options_changed)

        # Create the proxy widget to hold the speedometer
        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(self.speedometer)

        # Initialize with default value
        self.current_value = 0.0
        self.speedometer.update_value(self.current_value)

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

        # Extract numeric value from data
        try:
            # Try to get a numeric value from the data
            if isinstance(data, dict) and "value" in data:
                new_value = float(data["value"])
            elif isinstance(data, int | float):
                new_value = float(data)
            else:
                # Try to convert the entire data to a float
                text_value = get_structure_text(data)
                try:
                    new_value = float(text_value)
                except (ValueError, TypeError):
                    # If conversion fails, keep the current value
                    return

            # Update the speedometer if the value has changed
            if new_value != self.current_value:
                self.current_value = new_value
                self.speedometer.update_value(self.current_value)
        except (ValueError, TypeError):
            # If conversion fails, keep the current value
            pass

    def create_context_menu(self):
        menu = super().create_context_menu()

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.settings.show)
        menu.addAction(settings_action)

        return menu

    def options_changed(self, options: dict):
        self.options = options

        self.speedometer.set_enable_value_text(options.get("value_display", True))
        self.speedometer.set_enable_fine_scaled_marker(options.get("fine_tick_display", True))
        self.speedometer.set_enable_big_scaled_grid(options.get("coarse_tick_display", True))
        self.speedometer.set_enable_scale(options.get("scale_display", True))
        self.speedometer.set_scale_polygon_colors(options.get("scale", self.speedometer.scale_polygon_colors))
        self.speedometer.set_min_value(options.get("min", 0))
        self.speedometer.set_max_value(options.get("max", 100))

    def close(self):
        pass
