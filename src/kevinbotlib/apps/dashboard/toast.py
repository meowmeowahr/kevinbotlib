from dataclasses import dataclass
from enum import Enum

import qtawesome as qta
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsOpacityEffect, QHBoxLayout, QLabel, QMainWindow, QVBoxLayout, QWidget


@dataclass
class CustomSeverity:
    icon: str
    color: QColor


class Severity(Enum):
    Success = CustomSeverity("mdi6.check-bold", QColor("#31C376"))
    Info = CustomSeverity("mdi6.information-outline", QColor("#005C9F"))
    Warning = CustomSeverity("mdi6.alert", QColor("#FF9800"))
    Error = CustomSeverity("mdi6.alert-circle", QColor("#F44336"))
    Critical = CustomSeverity("mdi6.alert-octagon", QColor("#9C27B0"))


class NotificationWidget(QWidget):
    closed = Signal()

    def __init__(self, title: str, text: str, severity: CustomSeverity, duration: int, parent=None, *, bg: bool = True):
        super().__init__(parent)
        self.duration = duration
        self.setup_ui(title, text, severity)
        if duration != 0:
            self.setup_animations()
        self.setAutoFillBackground(bg)

    def setup_ui(self, title: str, text: str, severity: CustomSeverity):
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create content widget with background
        self.content = QWidget()
        self.content.setObjectName("notification")
        content_layout = QHBoxLayout(self.content)

        # Icon
        icon_label = qta.IconWidget()
        icon_label.setIconSize(32)
        icon_label.setIcon(qta.icon(severity.icon, color=severity.color.name()))
        content_layout.addWidget(icon_label)

        # Text content
        text_layout = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-weight: bold; color: {severity.color.name()}")
        text_layout.addWidget(title_label)

        message_label = QLabel(text)
        message_label.setWordWrap(True)
        text_layout.addWidget(message_label)

        content_layout.addLayout(text_layout, 3)
        layout.addWidget(self.content)

        # Style
        self.content.setStyleSheet(f"""
            QWidget#notification {{
                border: 2px solid {severity.color.name()};
                border-radius: 4px;
                padding: 8px;
            }}
        """)

        # Set fixed width but dynamic height
        self.adjustSize()

    def setup_animations(self):
        # Opacity effect for fade animations
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0)
        self.setGraphicsEffect(self.opacity_effect)

        # Fade in
        self.fade_in_timer = QTimer(self)
        self.fade_in_timer.timeout.connect(self._fade_in)
        self.fade_in_timer.start(10)

        # Display duration
        QTimer.singleShot(self.duration, self.start_fade_out)

        self.current_opacity = 0

    def _fade_in(self):
        self.current_opacity += 0.1
        if self.current_opacity >= 1:
            self.fade_in_timer.stop()
            self.current_opacity = 1
        self.opacity_effect.setOpacity(self.current_opacity)

    def start_fade_out(self):
        self.fade_out_timer = QTimer(self)
        self.fade_out_timer.timeout.connect(self._fade_out)
        self.fade_out_timer.start(10)

    def _fade_out(self):
        self.current_opacity -= 0.1
        if self.current_opacity <= 0:
            self.fade_out_timer.stop()
            self.close()
            self.closed.emit()
        self.opacity_effect.setOpacity(self.current_opacity)


class Notifier(QObject):
    def __init__(self, parent: QMainWindow):
        super().__init__(parent)
        self.notifications = []
        self.margin = 10
        self.parent_window = parent

    def toast(self, title: str, text: str, duration: int = 2500, severity: Severity | CustomSeverity = Severity.Info):
        if isinstance(severity, Severity):
            severity = severity.value

        notification = NotificationWidget(title, text, severity, duration, self.parent())
        notification.setFixedWidth(300)
        notification.closed.connect(lambda: self._remove_notification(notification))

        # Calculate position
        self._update_positions(notification)
        notification.show()
        self.notifications.append(notification)

    def _update_positions(self, new_notification=None):
        screen_geometry = self.parent_window.geometry()
        base_x = screen_geometry.width() - 300 - self.margin  # 300 is notification width
        current_y = screen_geometry.height() - self.margin - self.parent_window.statusBar().height()

        # Position existing notifications
        for notification in reversed(self.notifications):
            current_y -= notification.height() + self.margin
            notification.move(base_x, current_y)

        # Position new notification if provided
        if new_notification:
            current_y -= new_notification.height() + self.margin
            new_notification.move(base_x, current_y)

    def _remove_notification(self, notification):
        if notification in self.notifications:
            self.notifications.remove(notification)
            self._update_positions()  # Reposition remaining notifications
