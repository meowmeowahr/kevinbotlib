"""
The Speedometer Widget is based on work by Stefan Holstein under the Apache-2.0 license.
A copy of the license is included in the third_party/ folder of this repository.
"""

import math

from PySide6.QtCore import QObject, QPoint, QPointF, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QConicalGradient, QFont, QFontMetrics, QPainter, QPen, QPolygon, QPolygonF
from PySide6.QtWidgets import QWidget


class Speedometer(QWidget):
    """Fetches rows from a Bigtable.
    Args:
        none

    """

    value_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.NeedleColor = QColor(50, 50, 50, 255)
        self.ScaleValueColor = QColor(50, 50, 50, 255)
        self.DisplayValueColor = QColor(50, 50, 50, 255)
        self.CenterPointColor = QColor(50, 50, 50, 255)

        self.value_needle_count = 1
        self.value_needle = QObject
        self.change_value_needle_style(
            [QPolygon([QPoint(4, 4), QPoint(-4, 4), QPoint(-3, -120), QPoint(0, -126), QPoint(3, -120)])]
        )

        self.value_min = 0
        self.value_max = 1000
        self.value = self.value_min
        self.value_offset = 0
        self.value_needle_snapzone = 0.05
        self.last_value = 0

        # self.value2 = 0
        # self.value2Color = QColor(0, 0, 0, 255)

        self.gauge_color_outer_radius_factor = 1
        self.gauge_color_inner_radius_factor = 0.95
        self.center_horizontal_value = 0
        self.center_vertical_value = 0
        self.debug1 = None
        self.debug2 = None
        self.scale_angle_start_value = 135
        self.scale_angle_size = 270
        self.angle_offset = 0

        # self.scala_main_count = 10
        self.set_scala_main_count(10)
        self.scala_subdiv_count = 5

        self.pen = QPen(QColor(0, 0, 0))

        self.scale_polygon_colors = []
        self.set_scale_polygon_colors(
            [[0.00, QColor(Qt.red)], [0.1, QColor(Qt.yellow)], [0.15, QColor(Qt.green)], [1, QColor(Qt.transparent)]]
        )
        self.enable_scale = True

        # initialize Scale value text
        self.enable_scale_text = True
        self.initial_scale_fontsize = 15
        self.scale_fontsize = self.initial_scale_fontsize

        # initialize Main value text
        self.enable_value_text = True
        self.initial_value_fontsize = 40
        self.value_fontsize = self.initial_value_fontsize
        self.text_radius_factor = 0.7

        self.enable_fine_scaled_marker = True
        self.enable_big_scaled_marker = True

        self.needle_scale_factor = 0.6

        self.update()

        self.rescale_method()

    def rescale_method(self):
        # print("slotMethod")
        if self.width() <= self.height():
            self.widget_diameter = self.width()
        else:
            self.widget_diameter = self.height()

        self.change_value_needle_style(
            [
                QPolygonF(
                    [
                        QPoint(4, 30),
                        QPoint(-4, 30),
                        QPointF(-2, -self.widget_diameter / 2 * self.needle_scale_factor),
                        QPointF(0, -self.widget_diameter / 2 * self.needle_scale_factor - 6),
                        QPointF(2, -self.widget_diameter / 2 * self.needle_scale_factor),
                    ]
                )
            ]
        )

        self.scale_fontsize = self.initial_scale_fontsize * self.widget_diameter / 400
        self.value_fontsize = self.initial_value_fontsize * self.widget_diameter / 400

        # print("slotMethod end")

    def change_value_needle_style(self, design):
        # prepared for multiple needle instrument
        self.value_needle = []
        for i in design:
            self.value_needle.append(i)
        self.update()

    def update_value(self, value):
        if value <= self.value_min:
            self.value = self.value_min
        elif value >= self.value_max:
            self.value = self.value_max
        else:
            self.value = value

        self.value_changed.emit(int(value))
        self.update()

    def update_angle_offset(self, offset):
        self.angle_offset = offset
        self.update()

    def center_horizontal(self, value):
        self.center_horizontal_value = value

    def center_vertical(self, value):
        self.center_vertical_value = value

    def set_needle_color(self, color: QColor):
        self.NeedleColor = color

        self.update()

    def set_scale_value_color(self, color: QColor):
        self.ScaleValueColor = color

        self.update()

    def set_display_value_color(self, color: QColor):
        self.DisplayValueColor = color

        self.update()

    def set_center_point_color(self, color: QColor):
        self.CenterPointColor = color

        self.update()

    def set_enable_scale(self, enable: bool):
        self.enable_scale = enable

        self.update()

    def set_enable_scale_text(self, enable):
        self.enable_scale_text = enable

        self.update()

    def set_enable_value_text(self, enable):
        self.enable_value_text = enable

        self.update()

    def set_enable_big_scaled_grid(self, enable):
        self.enable_big_scaled_marker = enable

        self.update()

    def set_enable_fine_scaled_marker(self, enable):
        self.enable_fine_scaled_marker = enable

        self.update()

    def set_scala_main_count(self, count):
        if count < 1:
            count = 1
        self.scala_main_count = count

        self.update()

    def set_min_value(self, minval: float):
        if self.value < minval:
            self.value = minval
        if minval >= self.value_max:
            self.value_min = self.value_max - 1
        else:
            self.value_min = minval

        self.update()

    def set_max_value(self, maxval: float):
        if self.value > maxval:
            self.value = maxval
        if maxval <= self.value_min:
            self.value_max = self.value_min + 1
        else:
            self.value_max = maxval

        self.update()

    def set_start_scale_angle(self, value):
        # Value range in DEG: 0 - 360
        self.scale_angle_start_value = value

        self.update()

    def set_total_scale_angle_size(self, value):
        self.scale_angle_size = value

        self.update()

    def set_gauge_color_outer_radius_factor(self, value):
        self.gauge_color_outer_radius_factor = float(value) / 1000

        self.update()

    def set_gauge_color_inner_radius_factor(self, value):
        self.gauge_color_inner_radius_factor = float(value) / 1000

        self.update()

    def set_scale_polygon_colors(self, color_array):
        # print(type(color_array))
        if "list" in str(type(color_array)):
            self.scale_polygon_colors = [[point[0] * 0.78, point[1]] for point in color_array]
        elif color_array is None:
            self.scale_polygon_colors = [[0.0, Qt.transparent]]
        else:
            self.scale_polygon_colors = [[0.0, Qt.transparent]]

        self.update()

    ###############################################################################################
    # Get Methods
    ###############################################################################################

    def get_value_max(self):
        return self.value_max

    ###############################################################################################
    # Painter
    ###############################################################################################

    def create_polygon_pie(self, outer_radius, inner_raduis, start, lenght):
        polygon_pie = QPolygonF()
        n = 360  # angle steps size for full circle
        # changing n value will causes drawing issues
        w = 360 / n  # angle per step
        # create outer circle line from "start"-angle to "start + lenght"-angle
        x = 0
        y = 0

        for i in range(lenght + 1):  # add the points of polygon
            t = w * i + start - self.angle_offset
            x = outer_radius * math.cos(math.radians(t))
            y = outer_radius * math.sin(math.radians(t))
            polygon_pie.append(QPointF(x, y))
        # create inner circle line from "start + lenght"-angle to "start"-angle
        for i in range(lenght + 1):  # add the points of polygon
            # print("2 " + str(i))
            t = w * (lenght - i) + start - self.angle_offset
            x = inner_raduis * math.cos(math.radians(t))
            y = inner_raduis * math.sin(math.radians(t))
            polygon_pie.append(QPointF(x, y))

        # close outer line
        polygon_pie.append(QPointF(x, y))
        return polygon_pie

    def draw_filled_polygon(self, outline_pen_with=0):
        if self.scale_polygon_colors is not None:
            painter_filled_polygon = QPainter(self)
            painter_filled_polygon.setRenderHint(QPainter.RenderHint.Antialiasing)

            painter_filled_polygon.translate(self.width() / 2, self.height() / 2)

            painter_filled_polygon.setPen(Qt.PenStyle.NoPen)

            self.pen.setWidth(outline_pen_with)
            if outline_pen_with > 0:
                painter_filled_polygon.setPen(self.pen)

            colored_scale_polygon = self.create_polygon_pie(
                ((self.widget_diameter / 2) - (self.pen.width() / 2)) * self.gauge_color_outer_radius_factor,
                (((self.widget_diameter / 2) - (self.pen.width() / 2)) * self.gauge_color_inner_radius_factor),
                self.scale_angle_start_value,
                self.scale_angle_size,
            )

            QRect(QPoint(0, 0), QSize(self.widget_diameter / 2 - 1, self.widget_diameter - 1))
            grad = QConicalGradient(
                QPointF(0, 0), -self.scale_angle_size - self.scale_angle_start_value + self.angle_offset - 1
            )

            for eachcolor in self.scale_polygon_colors:
                grad.setColorAt(eachcolor[0], eachcolor[1])

            painter_filled_polygon.setBrush(grad)
            painter_filled_polygon.drawPolygon(colored_scale_polygon)

    def draw_big_scaled_markter(self):
        my_painter = QPainter(self)
        my_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Koordinatenursprung in die Mitte der Flaeche legen
        my_painter.translate(self.width() / 2, self.height() / 2)

        self.pen = QPen(self.ScaleValueColor)
        self.pen.setWidth(2)
        my_painter.setPen(self.pen)

        my_painter.rotate(self.scale_angle_start_value - self.angle_offset)
        steps_size = float(self.scale_angle_size) / float(self.scala_main_count)
        scale_line_outer_start = self.widget_diameter / 2
        scale_line_lenght = (self.widget_diameter / 2) - (self.widget_diameter / 20)
        for _i in range(self.scala_main_count + 1):
            my_painter.drawLine(scale_line_lenght, 0, scale_line_outer_start, 0)
            my_painter.rotate(steps_size)

    def create_scale_marker_values_text(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Koordinatenursprung in die Mitte der Flaeche legen
        painter.translate(self.width() / 2, self.height() / 2)
        font = QFont(self.fontInfo().family(), self.scale_fontsize)
        fm = QFontMetrics(font)

        pen_shadow = QPen()

        pen_shadow.setBrush(self.ScaleValueColor)
        painter.setPen(pen_shadow)

        text_radius_factor = 0.8
        text_radius = self.widget_diameter / 2 * text_radius_factor

        scale_per_div = (self.value_max - self.value_min) / self.scala_main_count

        angle_distance = float(self.scale_angle_size) / float(self.scala_main_count)
        for i in range(self.scala_main_count + 1):
            # text = str(int((self.value_max - self.value_min) / self.scala_main_count * i))
            text = str(round(self.value_min + scale_per_div * i, 2))
            w = fm.width(text) + 1
            h = fm.height()
            painter.setFont(QFont(self.fontInfo().family(), self.scale_fontsize))
            angle = angle_distance * i + float(self.scale_angle_start_value - self.angle_offset)
            x = text_radius * math.cos(math.radians(angle))
            y = text_radius * math.sin(math.radians(angle))
            text = [x - int(w / 2), y - int(h / 2), int(w), int(h), Qt.AlignmentFlag.AlignCenter, text]
            painter.drawText(text[0], text[1], text[2], text[3], text[4], text[5])

    def create_fine_scaled_marker(self):
        my_painter = QPainter(self)

        my_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Koordinatenursprung in die Mitte der Flaeche legen
        my_painter.translate(self.width() / 2, self.height() / 2)

        my_painter.setPen(self.ScaleValueColor)
        my_painter.rotate(self.scale_angle_start_value - self.angle_offset)
        steps_size = float(self.scale_angle_size) / float(self.scala_main_count * self.scala_subdiv_count)
        scale_line_outer_start = self.widget_diameter / 2
        scale_line_lenght = (self.widget_diameter / 2) - (self.widget_diameter / 40)
        for _i in range((self.scala_main_count * self.scala_subdiv_count) + 1):
            my_painter.drawLine(scale_line_lenght, 0, scale_line_outer_start, 0)
            my_painter.rotate(steps_size)

    def create_values_text(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Koordinatenursprung in die Mitte der Flaeche legen
        painter.translate(self.width() / 2, self.height() / 2)
        font = QFont(self.fontInfo().family(), self.value_fontsize)
        fm = QFontMetrics(font)

        pen_shadow = QPen()

        pen_shadow.setBrush(self.DisplayValueColor)
        painter.setPen(pen_shadow)

        text_radius = self.widget_diameter / 2 * self.text_radius_factor

        w = fm.width(str(self.value)) + 1
        h = fm.height()
        painter.setFont(QFont(self.fontInfo().family(), self.value_fontsize))

        angle_end = float(self.scale_angle_start_value + self.scale_angle_size - 360)
        angle = (angle_end - self.scale_angle_start_value) / 2 + self.scale_angle_start_value

        x = text_radius * math.cos(math.radians(angle))
        y = text_radius * math.sin(math.radians(angle))
        painter.drawText(x - w // 2, int(y - h // 2), w, h, Qt.AlignmentFlag.AlignCenter, str(self.value))

    def draw_big_needle_center_point(self, diameter=30):
        painter = QPainter(self)
        # painter.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Koordinatenursprung in die Mitte der Flaeche legen
        painter.translate(self.width() / 2, self.height() / 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.CenterPointColor)
        painter.drawEllipse(int(-diameter / 2), int(-diameter / 2), int(diameter), int(diameter))

    def draw_needle(self):
        painter = QPainter(self)
        # painter.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Koordinatenursprung in die Mitte der Flaeche legen
        painter.translate(self.width() / 2, self.height() / 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.NeedleColor)
        painter.rotate(
            (
                (self.value - self.value_offset - self.value_min)
                * self.scale_angle_size
                / (self.value_max - self.value_min)
            )
            + 90
            + self.scale_angle_start_value
        )

        painter.drawConvexPolygon(self.value_needle[0])

    def resizeEvent(self, _event):  # noqa: N802
        self.rescale_method()

    def paintEvent(self, _event):  # noqa: N802
        # colored pie area
        if self.enable_scale:
            self.draw_filled_polygon()

        # draw scale marker lines
        if self.enable_fine_scaled_marker:
            self.create_fine_scaled_marker()
        if self.enable_big_scaled_marker:
            self.draw_big_scaled_markter()

        # draw scale marker value text
        if self.enable_scale_text:
            self.create_scale_marker_values_text()

        # Display Value
        if self.enable_value_text:
            self.create_values_text()

        # draw needle 1
        self.draw_needle()

        # Draw Center Point
        self.draw_big_needle_center_point(diameter=(self.widget_diameter // 6))
