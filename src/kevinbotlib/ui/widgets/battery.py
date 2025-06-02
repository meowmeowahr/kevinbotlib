import math
from collections import deque
from dataclasses import dataclass
from typing import final

from PySide6.QtCore import QObject, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget


class BatteryGrapher(QWidget):
    """Qt widget to plot battery voltage over time."""

    def __init__(self, parent: QObject | None = None):
        """
        Create the widget

        Args:
            parent: Parent QObject of the widget. Defaults to None.
        """
        super().__init__(parent)
        self.data_points = deque()
        self.y_min = 0.0
        self.y_max = 100.0
        self.max_points = 50
        self.setMinimumSize(84, 64)

        self.border_color = self.palette().text().color()

    def add(self, value: float) -> None:
        """
        Add a new data point, scroll left if necessary.

        Args:
            value: New value to add
        """

        value = max(self.y_min, min(self.y_max, value))

        # Add a new point at the rightmost x position
        new_x = self.data_points[-1][0] + 1 if self.data_points else 0
        self.data_points.append((new_x, value))

        # Remove points that are too far left
        while self.data_points and self.data_points[0][0] < new_x - self.max_points:
            self.data_points.popleft()

        self.update()  # Trigger repaint

    def set_range(self, y_min: float, y_max: float) -> None:
        """
        Set the y-axis range for the graph.

        Args:
            y_min: Minimum Y value.
            y_max: Maximum Y value.
        """

        self.y_min = y_min
        self.y_max = y_max
        self.update()

    @final
    def _value_to_color(self, value):
        ratio = (value - self.y_min) / (self.y_max - self.y_min)
        if ratio < 0.5:  # noqa: PLR2004
            # Red to Yellow
            r = 255
            g = int(2 * ratio * 255)
            b = 0
        else:
            # Yellow to Green
            r = int(2 * (1 - ratio) * 255)
            g = 255
            b = 0
        return QColor(r, g, b)

    @final
    def paintEvent(self, _):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        margin = 10
        terminal_width = 10
        terminal_height = 8

        # Define battery shape
        path = QPainterPath()
        # Square terminals
        path.addRect(QRectF(margin + width / 20, margin, terminal_width, terminal_height))
        path.addRect(QRectF(width - margin - terminal_width - width / 20, margin, terminal_width, terminal_height))
        # Optionally rounded body
        body_top = margin + terminal_height
        body_height = height - body_top - margin
        path.addRoundedRect(QRectF(margin, body_top, width - 2 * margin, body_height), 8, 8)

        # Clip to battery shape
        painter.setClipPath(path)

        # Draw bars
        dp = self.data_points.copy()
        if dp:
            graph_width = width - 2 * margin
            max_x = max(x for x, _ in dp)
            bar_width = math.ceil(graph_width / self.max_points)  # Leave a gap between bars

            for x, y in dp:
                norm_x = margin + (x - (max_x - self.max_points)) * graph_width / self.max_points
                norm_y = body_top + (1 - (y - self.y_min) / (self.y_max - self.y_min)) * body_height
                bar_height = body_top + body_height - norm_y

                if margin <= norm_x <= width - margin:
                    color = self._value_to_color(y)
                    painter.setBrush(QBrush(color))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRoundedRect(QRectF(norm_x, norm_y, bar_width, bar_height), 3, 3)

        # Draw battery outline
        painter.setClipping(False)
        painter.setPen(QPen(self.border_color, 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)


@dataclass
class Battery:
    """Battery item to be used in BatteryManager."""

    voltage: float
    """Current battery voltage."""

    y_min: float
    """Minimum reasonable battery voltage."""

    y_max: float
    """Maximum reasonable battery voltage."""


class BatteryManager(QWidget):
    """Qt widget to display multiple BatteryGraphers and voltage labels."""

    def __init__(self, parent: QObject | None = None):
        """
        Create the widget.

        Args:
            parent: Parent QObject of the widget. Defaults to None.
        """

        super().__init__(parent)
        self.h_layout = QHBoxLayout(self)
        self.setLayout(self.h_layout)
        self.setMaximumHeight(200)
        self.graph_widgets = []

    def set(self, batts: list[Battery]) -> None:
        """
        Set the current battery voltages. Will update all graphs.

        Args:
            batts: List of batteries
        """

        # Resize graph_widgets if needed
        while len(self.graph_widgets) < len(batts):
            graph = BatteryGrapher()
            label = QLabel()
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            container = QVBoxLayout()
            container.addWidget(graph, stretch=1)
            container.addWidget(label)

            wrapper = QWidget()
            wrapper.setLayout(container)
            self.h_layout.addWidget(wrapper)

            self.graph_widgets.append((wrapper, graph, label))

        # Update each BatteryGrapher and QLabel
        for i, batt in enumerate(batts):
            _, graph, label = self.graph_widgets[i]
            graph.set_range(batt.y_min, batt.y_max)
            graph.add(batt.voltage)
            label.setText(f"{batt.voltage:.2f} V")

        # Hide any extra widgets if fewer batteries are passed
        for i in reversed(range(len(batts), len(self.graph_widgets))):
            w, graph, label = self.graph_widgets[i]
            self.h_layout.removeWidget(w)
            graph.setParent(None)
            label.setParent(None)
            self.graph_widgets.pop(i)
