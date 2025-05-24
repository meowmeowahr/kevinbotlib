from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGraphicsProxyWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from kevinbotlib.apps.common.settings_rows import Divider
from kevinbotlib.apps.dashboard.widgets.base import WidgetItem
from kevinbotlib.comm import RedisCommClient
from kevinbotlib.ui.widgets import BatteryGrapher

if TYPE_CHECKING:
    from kevinbotlib.apps.dashboard.app import GridGraphicsView


class BatteryWidgetSettings(QDialog):
    options_changed = Signal(dict)

    def __init__(self, options: dict | None = None, parent=None):
        super().__init__(parent)
        if not options:
            options = {}
        self.options = options

        self.setWindowTitle("Battery Voltage Settings")
        self.setModal(True)

        self.root_layout = QVBoxLayout()
        self.setLayout(self.root_layout)

        self.form = QFormLayout()
        self.root_layout.addLayout(self.form)

        self.form.addRow(Divider("Range"))

        self.min_value = QDoubleSpinBox()
        self.min_value.setValue(self.options.get("min", 0))
        self.min_value.setRange(0, 500)
        self.min_value.setDecimals(2)
        self.min_value.valueChanged.connect(self.set_min_value)
        self.form.addRow("Min Value", self.min_value)

        self.max_value = QDoubleSpinBox()
        self.max_value.setValue(self.options.get("max", 14))
        self.max_value.setRange(1, 500)
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

    def set_min_value(self, value: float):
        self.options["min"] = value

    def set_max_value(self, value: float):
        self.options["max"] = value

    def apply(self):
        self.options_changed.emit(self.options)


class BatteryWidgetItem(WidgetItem):
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
        self.kind = "battery"

        self.settings = BatteryWidgetSettings(self.options, grid)
        self.settings.options_changed.connect(self.options_changed)

        self.widget = QWidget()
        self.widget.setStyleSheet("background: transparent;")

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.widget.setLayout(self.layout)

        self.battery = BatteryGrapher()
        self.battery.setStyleSheet(f"background: transparent; color: {self.view.theme.value.foreground}")
        self.battery.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.battery.set_range(options.get("min", 5), options.get("max", 14))
        self.layout.addWidget(self.battery)

        self.label = QLabel("0.0V")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)

        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(self.widget)

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
        self.battery.add(data.get("value", 0.0))
        self.label.setText(f"{data.get('value', 0.0)}V")
        label_margin = self.margin + 30  # 30 is the title bar height
        self.proxy.setGeometry(
            self.margin, label_margin, self.width - 2 * self.margin, self.height - label_margin - self.margin
        )

    def create_context_menu(self):
        menu = super().create_context_menu()

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.settings.show)
        menu.addAction(settings_action)

        return menu

    def options_changed(self, options: dict):
        self.options = options
        self.battery.set_range(options.get("min", 5), options.get("max", 14))

    def close(self):
        pass
