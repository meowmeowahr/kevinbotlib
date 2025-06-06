from PySide6.QtCore import QPoint, QSettings, QSize, Qt
from PySide6.QtGui import QIcon, QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMdiSubWindow,
    QPushButton,
    QSizeGrip,
    QVBoxLayout,
    QWidget,
)


class _MdiTitleBar(QFrame):
    def __init__(self, parent: QMdiSubWindow, title: str) -> None:
        super().__init__(parent)
        self._parent = parent
        self._drag_position = QPoint()

        self.setObjectName("SimulatorMdiTitleBar")

        # Layout for title bar
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(0)

        # Title label
        self.title_label = QLabel(title, self)
        layout.addWidget(self.title_label)
        layout.addStretch()

        # Close button
        self.close_button = QPushButton(self)
        self.close_button.setIcon(QIcon(":/theme_icons/checkbox-indeterminate-light-2x.png"))
        self.close_button.setIconSize(QSize(16, 16))
        self.close_button.setFixedSize(QSize(24, 24))
        self.close_button.clicked.connect(parent.close)
        self.close_button.setFlat(True)
        layout.addWidget(self.close_button)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self._parent.pos()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._parent.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()


class _MdiChild(QMdiSubWindow):
    def __init__(self, winid: str, name: str, content: QWidget, settings: QSettings) -> None:
        super().__init__()
        self._name = name
        self._winid = winid
        self._settings = settings

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        main_widget = QWidget(self)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = _MdiTitleBar(self, name)
        self.title_bar.setFixedHeight(28)
        main_layout.addWidget(self.title_bar)

        main_layout.addWidget(content, 2)
        self.setWidget(main_widget)

        resize_grip = QSizeGrip(main_widget)
        main_layout.addWidget(resize_grip, alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._settings.setValue(f"windows/{self._winid}/geometry", self.saveGeometry())
        self._settings.setValue(f"windows/{self._winid}/visible", False)
        super().closeEvent(event)

    def moveEvent(self, event) -> None:  # noqa: N802
        pos = event.pos()
        area = self.mdiArea()  # Get the parent QMdiArea
        if area:  # Ensure area is not None
            # Check if the subwindow is trying to go out of bounds
            if pos.x() < 0:
                self.move(0, pos.y())
            if pos.y() < 0:
                self.move(pos.x(), 0)
            if pos.x() + self.width() > area.width():
                self.move(area.width() - self.width(), pos.y())
            if pos.y() + self.height() > area.height():
                self.move(pos.x(), area.height() - self.height())
