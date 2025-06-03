from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGraphicsProxyWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from superqt import QDoubleSlider

from kevinbotlib.apps.common.settings_rows import Divider
from kevinbotlib.apps.dashboard.widgets.base import WidgetItem
from kevinbotlib.comm import FloatSendable, IntegerSendable, RedisCommClient

if TYPE_CHECKING:
    from kevinbotlib.apps.dashboard.app import GridGraphicsView


class SliderWidgetSettings(QDialog):
    options_changed = Signal(dict)

    def __init__(self, options: dict | None = None, parent=None):
        super().__init__(parent)
        if not options:
            options = {}
        self.options = options

        self.setWindowTitle("Slider Widget Settings")
        self.setModal(True)

        self.root_layout = QVBoxLayout()
        self.setLayout(self.root_layout)

        self.form = QFormLayout()
        self.root_layout.addLayout(self.form)

        self.form.addRow(Divider("Range"))

        self.min_value = QDoubleSpinBox()
        self.min_value.setValue(self.options.get("min", 0))
        self.min_value.setRange(-10000, 10000)
        self.min_value.setDecimals(2)
        self.min_value.valueChanged.connect(self.set_min_value)
        self.form.addRow("Min Value", self.min_value)

        self.max_value = QDoubleSpinBox()
        self.max_value.setValue(self.options.get("max", 100))
        self.max_value.setRange(-10000, 10000)
        self.max_value.setDecimals(2)
        self.max_value.valueChanged.connect(self.set_max_value)
        self.form.addRow("Max Value", self.max_value)

        self.step_size = QDoubleSpinBox()
        self.step_size.setValue(self.options.get("step", 1.0))
        self.step_size.setRange(0.01, 1000)
        self.step_size.setDecimals(2)
        self.step_size.valueChanged.connect(self.set_step_size)
        self.form.addRow("Step Size", self.step_size)

        self.form.addRow(Divider("Appearance"))

        self.orientation_vertical = QCheckBox()
        self.orientation_vertical.setChecked(self.options.get("vertical", False))
        self.orientation_vertical.stateChanged.connect(self.set_orientation)
        self.form.addRow("Vertical Orientation", self.orientation_vertical)

        self.show_value = QCheckBox()
        self.show_value.setChecked(self.options.get("show_value", True))
        self.show_value.stateChanged.connect(self.set_show_value)
        self.form.addRow("Show Value Label", self.show_value)

        self.show_ticks = QCheckBox()
        self.show_ticks.setChecked(self.options.get("show_ticks", True))
        self.show_ticks.stateChanged.connect(self.set_show_ticks)
        self.form.addRow("Show Tick Marks", self.show_ticks)

        self.tick_interval = QSpinBox()
        self.tick_interval.setValue(self.options.get("tick_interval", 10))
        self.tick_interval.setRange(1, 1000)
        self.tick_interval.valueChanged.connect(self.set_tick_interval)
        self.form.addRow("Tick Interval", self.tick_interval)

        self.form.addRow(Divider("Behavior"))

        self.send_delay = QSpinBox()
        self.send_delay.setValue(self.options.get("send_delay_ms", 100))
        self.send_delay.setRange(0, 5000)
        self.send_delay.setSuffix(" ms")
        self.send_delay.valueChanged.connect(self.set_send_delay)
        self.form.addRow("Send Delay", self.send_delay)

        self.readonly = QCheckBox()
        self.readonly.setChecked(self.options.get("readonly", False))
        self.readonly.stateChanged.connect(self.set_readonly)
        self.form.addRow("Read Only", self.readonly)

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

    def set_step_size(self, value: float):
        self.options["step"] = value

    def set_orientation(self, checked: bool):
        self.options["vertical"] = checked

    def set_show_value(self, checked: bool):
        self.options["show_value"] = checked

    def set_show_ticks(self, checked: bool):
        self.options["show_ticks"] = checked

    def set_tick_interval(self, value: int):
        self.options["tick_interval"] = value

    def set_send_delay(self, value: int):
        self.options["send_delay_ms"] = value

    def set_readonly(self, checked: bool):
        self.options["readonly"] = checked

    def apply(self):
        self.options_changed.emit(self.options)


class SliderWidgetItem(WidgetItem):
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
        self.kind = "slider"
        self.client = _client
        self.grid = grid
        self.user_is_dragging = False
        self.last_received_value = 0.0
        self.raw_data = {}

        self.settings = SliderWidgetSettings(self.options, grid)
        self.settings.options_changed.connect(self.options_changed)

        self.send_timer = QTimer()
        self.send_timer.setSingleShot(True)
        self.send_timer.timeout.connect(self.send_value)
        self.pending_value = None

        self.widget = QWidget()
        self.widget.setStyleSheet("background: transparent;")

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.widget.setLayout(self.layout)

        self.slider: QDoubleSlider | None = None
        self.create_slider()
        self.value_label: QLabel | None = None
        self.create_value_label()

        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(self.widget)

        self.update_label_geometry()

    def create_slider(self):
        self.slider = QDoubleSlider()
        self.slider.setStyleSheet(self.view.window().styleSheet())

        orientation = Qt.Orientation.Vertical if self.options.get("vertical", False) else Qt.Orientation.Horizontal
        self.slider.setOrientation(orientation)

        min_val = self.options.get("min", 0.0)
        max_val = self.options.get("max", 100.0)
        step = self.options.get("step", 1.0)

        self.slider.setRange(min_val, max_val)
        self.slider.setSingleStep(step)

        if self.options.get("show_ticks", True):
            self.slider.setTickPosition(QDoubleSlider.TickPosition.TicksBothSides)
            self.slider.setTickInterval(self.options.get("tick_interval", 10))
        else:
            self.slider.setTickPosition(QDoubleSlider.TickPosition.NoTicks)

        self.slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.slider.setEnabled(not self.options.get("readonly", False))

        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderReleased.connect(self.on_slider_released)
        self.slider.valueChanged.connect(self.on_slider_value_changed)

        self.layout.addWidget(self.slider)

    def create_value_label(self):
        if self.options.get("show_value", True):
            self.value_label = QLabel("0.0")
            self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.value_label.setStyleSheet(f"color: {self.view.theme.value.foreground}")
            self.layout.addWidget(self.value_label)
        else:
            self.value_label = None

    def on_slider_pressed(self):
        self.user_is_dragging = True

    def on_slider_released(self):
        self.user_is_dragging = False
        self.send_value()

    def on_slider_value_changed(self, value: int):
        real_value = value

        if self.value_label:
            self.value_label.setText(f"{real_value:.2f}")

        if self.user_is_dragging:
            self.pending_value = real_value
            delay = self.options.get("send_delay_ms", 100)
            if delay > 0:
                self.send_timer.start(delay)
            else:
                self.send_value()

    def send_value(self):
        if self.pending_value is not None and not self.options.get("readonly", False):
            if self.raw_data:
                if self.raw_data["did"] == "kevinbotlib.dtype.float":
                    self.client.set(
                        self.key,
                        FloatSendable(
                            value=self.pending_value,
                            struct=self.raw_data.get("struct", FloatSendable(value=0).struct),
                            timeout=self.raw_data.get("timeout", None),
                            flags=self.raw_data.get("flags", []),
                        ),
                    )
                elif self.raw_data["did"] == "kevinbotlib.dtype.int":
                    self.client.set(
                        self.key,
                        IntegerSendable(
                            value=int(self.pending_value),
                            struct=self.raw_data.get("struct", IntegerSendable(value=0).struct),
                            timeout=self.raw_data.get("timeout", None),
                            flags=self.raw_data.get("flags", []),
                        ),
                    )
                else:
                    msg = f"Unsupported data type: {self.raw_data['did']}"
                    raise ValueError(msg)

            self.pending_value = None

    def update_label_geometry(self):
        label_margin = self.margin + 30
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
        self.raw_data = data

        if self.user_is_dragging:
            return

        new_value = data.get("value", 0.0)
        self.last_received_value = new_value

        slider_value = new_value
        self.slider.blockSignals(True)
        self.slider.setValue(slider_value)
        self.slider.blockSignals(False)

        if self.value_label:
            self.value_label.setText(f"{new_value:.2f}")

        self.update_label_geometry()

    def create_context_menu(self):
        menu = super().create_context_menu()

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.settings.show)
        menu.addAction(settings_action)

        return menu

    def options_changed(self, options: dict):
        self.options = options

        self.layout.removeWidget(self.slider)
        self.slider.deleteLater()

        if self.value_label:
            self.layout.removeWidget(self.value_label)
            self.value_label.deleteLater()
            self.value_label = None

        self.create_slider()
        self.create_value_label()

        if hasattr(self, "last_received_value"):
            self.slider.setValue(self.last_received_value)
            if self.value_label:
                self.value_label.setText(f"{self.last_received_value:.2f}")

    def close(self):
        if self.send_timer.isActive():
            self.send_timer.stop()
