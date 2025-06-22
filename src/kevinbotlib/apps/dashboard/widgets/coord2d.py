import math
from enum import Enum
from typing import TYPE_CHECKING, Any

import superqt
from PySide6.QtCore import QPointF, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QFont, QPainter, QPaintEvent, QPen
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
    QWidget,
)

from kevinbotlib.apps.common.settings_rows import Divider
from kevinbotlib.apps.dashboard.widgets.base import WidgetItem
from kevinbotlib.comm.redis import RedisCommClient

if TYPE_CHECKING:
    from kevinbotlib.apps.dashboard.app import GridGraphicsView


class GraphColors(Enum):
    Red = "#b44646"
    Green = "#46b482"
    Blue = "#4682b4"
    White = "#e4e4e4"
    Black = "#060606"
    Yellow = "#e4e446"
    Magenta = "#b446b4"


class GraphShapes(Enum):
    Circle = "circle"
    Triangle = "triangle"
    Square = "square"
    Cross = "cross"
    Line = "line"
    Arrow = "arrow"


class GraphWidget(QWidget):
    def __init__(self, background_color="#2e2e2e", parent=None):
        super().__init__(parent)
        self.background_color = QColor(background_color)
        self.data_points = []
        self.options = {}
        self.margin = 40
        self.grid_alpha = 0.3

        # Default options
        self.auto_scale = True
        self.min_x = 0
        self.max_x = 100
        self.min_y = 0
        self.max_y = 100
        self.pt_color = QColor("#4682b4")
        self.pt_shape = "circle"
        self.pt_width = 20

        self.setMinimumSize(200, 150)

    def set_options(self, options: dict):
        self.options = options
        self.auto_scale = options.get("auto_scale", True)
        self.min_x = options.get("min_x", 0)
        self.max_x = options.get("max_x", 100)
        self.min_y = options.get("min_y", 0)
        self.max_y = options.get("max_y", 100)
        self.pt_color = QColor(GraphColors(options.get("color", "#4682b4")).value)
        self.pt_shape = options.get("shape", "circle")
        self.pt_width = options.get("width", 10)
        self.update()

    def set_data(self, data_points: list):
        self.data_points = data_points
        self.update()

    def calculate_bounds(self):
        if not self.data_points:
            return self.min_x, self.max_x, self.min_y, self.max_y

        if self.auto_scale:
            x_values = [point[0] for point in self.data_points]
            y_values = [point[1] for point in self.data_points]

            min_x = min(x_values) if x_values else 0
            max_x = max(x_values) if x_values else 100
            min_y = min(y_values) if y_values else 0
            max_y = max(y_values) if y_values else 100

            # Add some padding
            x_range = max_x - min_x if max_x != min_x else 1
            y_range = max_y - min_y if max_y != min_y else 1

            min_x -= x_range * 0.05
            max_x += x_range * 0.05
            min_y -= y_range * 0.05
            max_y += y_range * 0.05

            return min_x, max_x, min_y, max_y
        return self.min_x, self.max_x, self.min_y, self.max_y

    def data_to_screen(self, x, y, plot_rect, min_x, max_x, min_y, max_y):
        """Convert data coordinates to screen coordinates"""
        if max_x == min_x:
            screen_x = plot_rect.left() + plot_rect.width() / 2
        else:
            screen_x = plot_rect.left() + (x - min_x) / (max_x - min_x) * plot_rect.width()

        if max_y == min_y:
            screen_y = plot_rect.top() + plot_rect.height() / 2
        else:
            screen_y = plot_rect.bottom() - (y - min_y) / (max_y - min_y) * plot_rect.height()

        return screen_x, screen_y

    def draw_grid(self, painter: QPainter, plot_rect: QRect, min_x, max_x, min_y, max_y):
        """Draw grid lines"""
        grid_color = QColor(255, 255, 255, int(255 * self.grid_alpha))
        grid_pen = QPen(grid_color, 1)
        painter.setPen(grid_pen)

        # Calculate grid spacing
        x_range = max_x - min_x
        y_range = max_y - min_y

        # Determine number of grid lines (aim for ~10)
        x_step = self.calculate_nice_step(x_range / 10)
        y_step = self.calculate_nice_step(y_range / 10)

        # Draw vertical grid lines
        x = math.ceil(min_x / x_step) * x_step
        while x <= max_x:
            screen_x, _ = self.data_to_screen(x, 0, plot_rect, min_x, max_x, min_y, max_y)
            painter.drawLine(int(screen_x), plot_rect.top(), int(screen_x), plot_rect.bottom())
            x += x_step

        # Draw horizontal grid lines
        y = math.ceil(min_y / y_step) * y_step
        while y <= max_y:
            _, screen_y = self.data_to_screen(0, y, plot_rect, min_x, max_x, min_y, max_y)
            painter.drawLine(plot_rect.left(), int(screen_y), plot_rect.right(), int(screen_y))
            y += y_step

    def calculate_nice_step(self, rough_step):
        """Calculate a 'nice' step size for grid lines"""
        if rough_step <= 0:
            return 1

        magnitude = 10 ** math.floor(math.log10(rough_step))
        normalized = rough_step / magnitude

        if normalized <= 1:
            return magnitude
        if normalized <= 2:  # noqa: PLR2004
            return 2 * magnitude
        if normalized <= 5:  # noqa: PLR2004
            return 5 * magnitude
        return 10 * magnitude

    def draw_axes_labels(self, painter: QPainter, plot_rect: QRect, min_x, max_x, min_y, max_y):
        """Draw axis labels"""
        font = QFont("Arial", 8)
        painter.setFont(font)
        painter.setPen(QPen(QColor(200, 200, 200), 1))

        # Calculate step sizes
        x_range = max_x - min_x
        y_range = max_y - min_y
        x_step = self.calculate_nice_step(x_range / 5)
        y_step = self.calculate_nice_step(y_range / 5)

        # Draw X axis labels
        x = math.ceil(min_x / x_step) * x_step
        while x <= max_x:
            screen_x, _ = self.data_to_screen(x, 0, plot_rect, min_x, max_x, min_y, max_y)
            label = f"{x:.1f}" if x_step < 1 else f"{int(x)}"
            painter.drawText(int(screen_x - 20), plot_rect.bottom() + 15, 40, 20, 0x84, label)
            x += x_step

        # Draw Y axis labels
        y = math.ceil(min_y / y_step) * y_step
        while y <= max_y:
            _, screen_y = self.data_to_screen(0, y, plot_rect, min_x, max_x, min_y, max_y)
            label = f"{y:.1f}" if y_step < 1 else f"{int(y)}"
            painter.drawText(5, int(screen_y - 10), 30, 20, 0x82, label)
            y += y_step

    def paintEvent(self, _event: QPaintEvent):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        painter.fillRect(self.rect(), self.background_color)

        plot_rect = QRect(self.margin, 10, self.width() - self.margin - 10, self.height() - self.margin - 10)

        if plot_rect.width() <= 0 or plot_rect.height() <= 0:
            return

        min_x, max_x, min_y, max_y = self.calculate_bounds()

        self.draw_grid(painter, plot_rect, min_x, max_x, min_y, max_y)

        self.draw_axes_labels(painter, plot_rect, min_x, max_x, min_y, max_y)

        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.drawRect(plot_rect)

        line_pen = QPen(self.pt_color, self.pt_width)
        painter.setPen(line_pen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        points = []
        for x, y, _ in self.data_points:
            screen_x, screen_y = self.data_to_screen(x, y, plot_rect, min_x, max_x, min_y, max_y)
            points.append(QPointF(screen_x, screen_y))

        for i in range(len(points)):
            painter.save()
            painter.translate(points[i].x(), points[i].y())
            painter.rotate(math.degrees(self.data_points[i][2]))
            match self.pt_shape:
                case "square":
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QBrush(self.pt_color))
                    painter.drawRect(-self.pt_width // 2, -self.pt_width // 2, self.pt_width, self.pt_width)
                case "circle":
                    painter.drawEllipse(-self.pt_width // 2, -self.pt_width // 2, self.pt_width, self.pt_width)
                case "line":
                    line_pen = QPen(self.pt_color, self.pt_width // 2)
                    painter.setPen(line_pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawLine(QPointF(0, -self.pt_width // 2), QPointF(0, self.pt_width // 2))
                case "cross":
                    line_pen = QPen(self.pt_color, self.pt_width // 2)
                    painter.setPen(line_pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawLine(QPointF(0, -self.pt_width // 2), QPointF(0, self.pt_width // 2))
                    painter.drawLine(QPointF(-self.pt_width // 2, 0), QPointF(self.pt_width // 2, 0))
                case "arrow":
                    line_pen = QPen(self.pt_color, self.pt_width // 3)
                    line_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                    painter.setPen(line_pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawLine(QPointF(0, -self.pt_width // 2), QPointF(0, self.pt_width // 2))
                    painter.drawLine(QPointF(0, -self.pt_width // 2), QPointF(self.pt_width // 2, 0))
                    painter.drawLine(QPointF(0, -self.pt_width // 2), QPointF(-self.pt_width // 2, 0))
                case _:
                    msg = f"Unsupported point shape: {self.pt_shape}"
                    raise NotImplementedError(msg)
            painter.restore()


class Coord2dWidgetSettings(QDialog):
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
        self.form.addRow("Auto Scale Axes", self.auto_scale)

        self.min_x = QDoubleSpinBox()
        self.min_x.setValue(self.options.get("min_x", 0))
        self.min_x.setRange(-2_147_483_648, 2_147_483_647)
        self.min_x.setDecimals(2)
        self.min_x.setEnabled(not self.options.get("auto_scale", False))
        self.min_x.valueChanged.connect(self.set_min_x)
        self.min_x.setDisabled(self.options.get("auto_scale", True))
        self.form.addRow("Min X Value", self.min_x)

        self.max_x = QDoubleSpinBox()
        self.max_x.setValue(self.options.get("max_x", 100))
        self.max_x.setRange(-2_147_483_648, 2_147_483_647)
        self.max_x.setDecimals(2)
        self.max_x.setEnabled(not self.options.get("auto_scale", False))
        self.max_x.valueChanged.connect(self.set_max_x)
        self.max_x.setDisabled(self.options.get("auto_scale", True))
        self.form.addRow("Max X Value", self.max_x)

        self.min_y = QDoubleSpinBox()
        self.min_y.setValue(self.options.get("min_y", 0))
        self.min_y.setRange(-2_147_483_648, 2_147_483_647)
        self.min_y.setDecimals(2)
        self.min_y.setEnabled(not self.options.get("auto_scale", False))
        self.min_y.valueChanged.connect(self.set_min_y)
        self.min_y.setDisabled(self.options.get("auto_scale", True))
        self.form.addRow("Min Y Value", self.min_y)

        self.max_y = QDoubleSpinBox()
        self.max_y.setValue(self.options.get("max_y", 100))
        self.max_y.setRange(-2_147_483_648, 2_147_483_647)
        self.max_y.setDecimals(2)
        self.max_y.setEnabled(not self.options.get("auto_scale", False))
        self.max_y.valueChanged.connect(self.set_max_y)
        self.max_y.setDisabled(self.options.get("auto_scale", True))
        self.form.addRow("Max Y Value", self.max_y)

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
        self.form.addRow("Point Color", self.color)

        self.shape = superqt.QEnumComboBox()
        self.shape.setEnumClass(GraphShapes)
        self.shape.setCurrentEnum(GraphShapes(self.options.get("shape", "circle")))
        self.shape.currentEnumChanged.connect(self.set_shape)
        self.form.addRow("Point Shape", self.shape)

        self.width = QSpinBox(minimum=6, maximum=20, value=self.options.get("width", 10))
        self.width.valueChanged.connect(self.set_width)
        self.form.addRow("Point Size", self.width)

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

    def set_shape(self, shape: GraphShapes):
        self.options["shape"] = shape.value

    def set_width(self, width: int):
        self.options["width"] = width

    def set_points(self, points: int):
        self.options["points"] = points

    def set_interval(self, interval: int):
        self.options["interval"] = interval

    def set_auto_scale(self, state: int):
        self.options["auto_scale"] = bool(state)
        self.min_x.setEnabled(not self.options["auto_scale"])
        self.max_x.setEnabled(not self.options["auto_scale"])
        self.min_y.setEnabled(not self.options["auto_scale"])
        self.max_y.setEnabled(not self.options["auto_scale"])

    def set_min_x(self, value: float):
        self.options["min_x"] = value

    def set_max_x(self, value: float):
        self.options["max_x"] = value

    def set_min_y(self, value: float):
        self.options["min_y"] = value

    def set_max_y(self, value: float):
        self.options["max_y"] = value

    def apply(self):
        self.options_changed.emit(self.options)


class Coord2dWidgetItem(WidgetItem):
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
        self.kind = "coord2d"
        self.min_width = self.grid_size * 4
        self.min_height = self.grid_size * 3

        self.graph = GraphWidget(
            background_color=grid.theme.value.item_background,
        )
        self.graph.set_options(self.options)

        self.settings = Coord2dWidgetSettings(self.graph, self.options, grid)
        self.settings.options_changed.connect(self.options_changed)

        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(self.graph)

        self.data_points = []

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
        match data["did"]:
            case "kevinbotlib.dtype.coord2d" | "kevinbotlib.dtype.coord3d":
                if "x" in data["value"] and "y" in data["value"]:
                    x_value = data["value"]["x"]
                    y_value = data["value"]["y"]
                    self.data_points = [(x_value, y_value, 0.0)]
            case "kevinbotlib.dtype.list.coord2d" | "kevinbotlib.dtype.list.coord3d":
                self.data_points = [(c["x"], c["y"], 0.0) for c in data["value"]]
            case "kevinbotlib.dtype.pose2d" | "kevinbotlib.dtype.pose3d":
                if "transform" in data["value"] and "orientation" in data["value"]:
                    x_value = data["value"]["transform"]["x"]
                    y_value = data["value"]["transform"]["y"]
                    theta_value = data["value"]["orientation"]["radians"]
                    self.data_points = [(x_value, y_value, theta_value)]
            case "kevinbotlib.dtype.list.pose2d" | "kevinbotlib.dtype.list.pose3d":
                self.data_points = [
                    (c["transform"]["x"], c["transform"]["y"], c["orientation"]["radians"]) for c in data["value"]
                ]

    def create_context_menu(self):
        menu = super().create_context_menu()
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.settings.show)
        menu.addAction(settings_action)
        return menu

    def options_changed(self, options: dict):
        self.options = options
        self.timer.setInterval(self.options.get("interval", 50))
        self.graph.set_options(self.options)

    def worker_update(self):
        self.graph.set_data(self.data_points)

    def close(self):
        self.timer.stop()
