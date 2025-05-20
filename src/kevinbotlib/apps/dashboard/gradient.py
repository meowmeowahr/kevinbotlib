from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class GradientStopDialog(QDialog):
    """
    A custom dialog for editing a single gradient stop (position and color).
    """

    def __init__(self, initial_pos: float = 0.0, initial_color: QColor | None = None, parent=None):
        super().__init__(parent)
        if not initial_color:
            initial_color = QColor(0, 0, 0)
        self.setWindowTitle("Edit Gradient Stop")
        self.setModal(True)  # Make it modal so parent windows are blocked

        self._position = initial_pos
        self._color = initial_color

        self.layout = QVBoxLayout(self)

        # Position Input
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("Position (0.0 - 1.0):"))
        self.pos_spinbox = QDoubleSpinBox()
        self.pos_spinbox.setRange(0.0, 1.0)
        self.pos_spinbox.setSingleStep(0.01)
        self.pos_spinbox.setDecimals(3)  # Allow for 3 decimal places
        self.pos_spinbox.setValue(initial_pos)
        pos_layout.addWidget(self.pos_spinbox)
        self.layout.addLayout(pos_layout)

        # Color Picker
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Color:"))
        self.color_button = QPushButton("Choose Color")
        self.color_button.clicked.connect(self._choose_color)
        color_layout.addWidget(self.color_button)

        self.color_swatch = QFrame()
        self.color_swatch.setFixedSize(QSize(30, 30))
        self.color_swatch.setFrameShape(QFrame.StyledPanel)
        self.color_swatch.setFrameShadow(QFrame.Sunken)
        color_layout.addWidget(self.color_swatch)
        self.layout.addLayout(color_layout)

        self._update_color_swatch()  # Set initial color on swatch

        # OK and Cancel Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def _update_color_swatch(self):
        """Updates the color swatch QFrame background."""
        self.color_swatch.setStyleSheet(f"background-color: {self._color.name()};")

    def _choose_color(self):
        """Opens the QColorDialog and updates the internal color."""
        color_dialog = QColorDialog(self)
        color_dialog.setCurrentColor(self._color)
        if color_dialog.exec():
            self._color = color_dialog.selectedColor()
            self._update_color_swatch()

    def get_position(self):
        """Returns the selected position."""
        return self.pos_spinbox.value()

    def get_color(self):
        """Returns the selected color."""
        return self._color


class GradientEditor(QWidget):
    """
    A PySide6 widget for editing a linear gradient defined by a list of [float, QColor] tuples.
    This version is text-based with a list and explicit Add/Edit/Delete buttons.
    """

    gradient_changed = Signal(list)  # Emits the updated list of [float, QColor]

    def __init__(self, initial_gradient_stops=None, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 200)

        # Initialize with [float, QColor]
        # Ensure at least two stops for a meaningful gradient
        if initial_gradient_stops and len(initial_gradient_stops) >= 2:  # noqa: PLR2004
            self.gradient_stops = sorted(initial_gradient_stops, key=lambda x: x[0])
        else:
            self.gradient_stops = [
                [0.0, QColor(0, 0, 0)],  # Black at the start
                [1.0, QColor(255, 255, 255)],  # White at the end
            ]

        self.layout = QVBoxLayout(self)

        self.stop_list_widget = QListWidget()
        self.stop_list_widget.itemDoubleClicked.connect(self._edit_selected_stop)  # Double-click to edit
        self.layout.addWidget(self.stop_list_widget)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add")
        self.edit_button = QPushButton("Edit")
        self.delete_button = QPushButton("Delete")

        self.add_button.clicked.connect(self._add_new_stop)
        self.edit_button.clicked.connect(self._edit_selected_stop)
        self.delete_button.clicked.connect(self._delete_selected_stop)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)

        self.layout.addLayout(button_layout)

        self._update_list_widget()

    def _update_list_widget(self):
        """Refreshes the QListWidget with current gradient stops."""
        self.stop_list_widget.clear()
        swatch_size = QSize(20, 20)

        for pos, color in self.gradient_stops:
            item_text = f"Position: {pos:.3f}, Color: ({color.red()}, {color.green()}, {color.blue()})"
            item = QListWidgetItem(item_text)

            color_pixmap = QPixmap(swatch_size)
            color_pixmap.fill(color)
            item.setIcon(color_pixmap)
            item.setData(Qt.UserRole, [pos, color])  # Store the actual data in UserRole

            self.stop_list_widget.addItem(item)

        self.gradient_changed.emit(self.gradient_stops)

    def _add_new_stop(self):
        """Handles adding a new gradient stop using the combined dialog."""
        initial_pos = 0.5
        initial_color = QColor(128, 128, 128)  # Default grey

        # Try to find a sensible default position and color for new stop
        if self.stop_list_widget.currentRow() != -1:
            selected_index = self.stop_list_widget.currentRow()
            current_pos = self.gradient_stops[selected_index][0]
            current_color = self.gradient_stops[selected_index][1]

            if selected_index + 1 < len(self.gradient_stops):
                next_pos = self.gradient_stops[selected_index + 1][0]
                next_color = self.gradient_stops[selected_index + 1][1]
                initial_pos = (current_pos + next_pos) / 2.0
                # Interpolate color between selected and next stop
                interp_factor = (initial_pos - current_pos) / (next_pos - current_pos)
                r = int(current_color.red() + (next_color.red() - current_color.red()) * interp_factor)
                g = int(current_color.green() + (next_color.green() - current_color.green()) * interp_factor)
                b = int(current_color.blue() + (next_color.blue() - current_color.blue()) * interp_factor)
                initial_color = QColor(r, g, b)
            elif selected_index > 0:  # If at the end, use the previous stop's color
                prev_pos = self.gradient_stops[selected_index - 1][0]
                initial_pos = (current_pos + prev_pos) / 2.0  # Midpoint with previous
                initial_color = current_color  # Keep current color for now, or use prev_color

        dialog = GradientStopDialog(initial_pos, initial_color, self)
        if dialog.exec():
            new_pos = dialog.get_position()
            new_color = dialog.get_color()

            # Check for existing stop at this position
            for existing_pos, _ in self.gradient_stops:
                if abs(existing_pos - new_pos) < 0.0001:  # Use a small epsilon for float comparison # noqa: PLR2004
                    QMessageBox.warning(self, "Add Error", "A gradient stop already exists at this position.")
                    return

            self.gradient_stops.append([new_pos, new_color])
            self.gradient_stops.sort(key=lambda x: x[0])  # Keep sorted
            self._update_list_widget()

    def _edit_selected_stop(self):
        """Handles editing the selected gradient stop using the combined dialog."""
        current_row = self.stop_list_widget.currentRow()
        if current_row == -1:
            QMessageBox.warning(self, "Edit Error", "No gradient stop selected to edit.")
            return

        current_pos, current_color = self.gradient_stops[current_row]

        dialog = GradientStopDialog(current_pos, current_color, self)
        if dialog.exec():
            new_pos = dialog.get_position()
            new_color = dialog.get_color()

            # Check for existing stop at this new position (excluding the current one)
            for i, (existing_pos, _) in enumerate(self.gradient_stops):
                if i != current_row and abs(existing_pos - new_pos) < 0.0001:  # noqa: PLR2004
                    QMessageBox.warning(self, "Edit Error", "A gradient stop already exists at this new position.")
                    return

            self.gradient_stops[current_row] = [new_pos, new_color]
            self.gradient_stops.sort(key=lambda x: x[0])  # Keep sorted
            self._update_list_widget()

    def _delete_selected_stop(self):
        """Handles deleting the selected gradient stop."""
        current_row = self.stop_list_widget.currentRow()
        if current_row == -1:
            QMessageBox.warning(self, "Delete Error", "No gradient stop selected to delete.")
            return

        if len(self.gradient_stops) <= 2:  # noqa: PLR2004
            QMessageBox.warning(self, "Delete Error", "Cannot delete a stop if only two remain (minimum required).")
            return

        reply = QMessageBox.question(
            self,
            "Delete Stop",
            "Are you sure you want to delete this gradient stop?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.gradient_stops.pop(current_row)
            self._update_list_widget()

    def get_gradient_stops(self):
        return self.gradient_stops

    def set_gradient_stops(self, stops):
        # Ensure the incoming list is [float, QColor] and sort it, minimum 2 stops
        if stops and len(stops) >= 2:  # noqa: PLR2004
            self.gradient_stops = sorted(stops, key=lambda x: x[0])
        else:
            # Fallback to default if invalid input
            self.gradient_stops = [[0.0, QColor(0, 0, 0)], [1.0, QColor(255, 255, 255)]]
            QMessageBox.warning(self, "Invalid Gradient", "Initial gradient must have at least two stops. Defaulting.")

        self._update_list_widget()
