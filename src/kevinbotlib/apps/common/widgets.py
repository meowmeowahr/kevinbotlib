from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QLabel,
    QProgressBar,
    QScrollArea,
    QStackedWidget,
    QStyle,
    QStyleOption,
    QVBoxLayout,
    QWidget,
)


class QWidgetList(QScrollArea):
    def __init__(self):
        super().__init__()

        self.setWidgetResizable(True)
        self.container = QWidget(self)
        self.container.setStyleSheet("QWidget {background: transparent;}")
        self.setWidget(self.container)
        self.root_layout = QVBoxLayout(self.container)
        self.root_layout.setSpacing(5)
        self.root_layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        self.root_layout.addWidget(self.stack)

        # --- List view
        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setSpacing(5)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.stack.addWidget(self.list_widget)

        # --- Loading/progress view
        self.loading_widget = QWidget()
        self.loading_layout = QVBoxLayout(self.loading_widget)
        self.loading_layout.setSpacing(10)

        self.loading_label = QLabel("Please Wait...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setValue(0)

        self.loading_layout.addStretch()
        self.loading_layout.addWidget(self.loading_label)
        self.loading_layout.addWidget(self.progress_bar)
        self.loading_layout.addStretch()

        self.loading_widget.setLayout(self.loading_layout)
        self.stack.addWidget(self.loading_widget)

        self.list_layout.addStretch()

    def add_widget(self, widget: QWidget):
        """Add a widget to the list."""
        self.list_layout.insertWidget(self.list_layout.count() - 1, widget)

    def remove_widget(self, widget: QWidget):
        """Remove a specific widget from the list."""
        self.list_layout.removeWidget(widget)
        widget.setParent(None)

    def clear_widgets(self):
        """Remove all widgets from the list."""
        while self.list_layout.count() - 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

    def set_spacing(self, spacing: int):
        """Set spacing between widgets."""
        self.list_layout.setSpacing(spacing)

    def set_loading(self, loading: bool):
        """Show or hide the loading/progress screen."""
        if loading:
            self.stack.setCurrentWidget(self.loading_widget)
        else:
            self.stack.setCurrentWidget(self.list_widget)

    def set_progress(self, value: int, text: str = ""):
        """Update progress bar value and optional text."""
        self.progress_bar.setValue(value)
        if text:
            self.loading_label.setText(text)


class WrapAnywhereLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.textalignment = Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWrapAnywhere
        self.isTextLabel = True
        self.align = None

    def paintEvent(self, _event):  # noqa: N802
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)

        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)

        self.style().drawItemText(painter, self.rect(), self.textalignment, self.palette(), True, self.text())
