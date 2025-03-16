from functools import partial
from typing import override

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from kevinbotlib.exceptions import JoystickMissingException
from kevinbotlib.joystick import LocalJoystickIdentifiers, POVDirection, RawLocalJoystickDevice
from kevinbotlib.logger import Logger


class ActiveItemDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index):
        is_active = index.data(Qt.ItemDataRole.UserRole + 1)
        if is_active:
            painter.fillRect(option.rect, QColor("green"))
        super().paint(painter, option, index)


class ButtonGridWidget(QGroupBox):
    def __init__(self, max_buttons: int = 32):
        super().__init__("Buttons")
        self.max_buttons = max_buttons
        self.button_count = 0
        self.button_labels = []
        self.init_ui()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def init_ui(self):
        self.root_layout = QGridLayout()
        self.root_layout.setSpacing(4)
        self.setLayout(self.root_layout)

        square_size = 12
        for _ in range(self.max_buttons):
            label = QLabel()
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFixedSize(square_size, square_size)
            label.setObjectName("ButtonInputStateBoxInactive")
            label.setVisible(False)
            self.button_labels.append(label)

        self.update_grid_layout()

    def set_button_count(self, count: int):
        self.button_count = min(count, self.max_buttons)
        for i in range(self.max_buttons):
            self.button_labels[i].setVisible(i < self.button_count)
        self.update_grid_layout()

    def set_button_state(self, button_id: int, state: bool):
        if 0 <= button_id < self.button_count:
            self.button_labels[button_id].setObjectName(
                "ButtonInputStateBoxActive" if state else "ButtonInputStateBoxInactive"
            )
            self.style().polish(self.button_labels[button_id])

    def update_grid_layout(self):
        if self.button_count == 0:
            return
        for i in range(self.button_count):
            row = i % 8
            col = i // 8
            self.root_layout.addWidget(self.button_labels[i], row, col)


class POVGridWidget(QGroupBox):
    def __init__(self):
        super().__init__("POV")
        self.pov_labels = {}
        self.init_ui()

    def init_ui(self):
        self.root = QVBoxLayout()
        self.setLayout(self.root)

        self.root.addStretch()

        self.grid = QGridLayout()
        self.grid.setSpacing(4)
        self.root.addLayout(self.grid)

        self.root.addStretch()

        square_size = 16  # Slightly larger for visibility
        # Define the 3x3 grid positions for POV directions
        pov_positions = {
            POVDirection.UP: (0, 1),
            POVDirection.UP_RIGHT: (0, 2),
            POVDirection.RIGHT: (1, 2),
            POVDirection.DOWN_RIGHT: (2, 2),
            POVDirection.DOWN: (2, 1),
            POVDirection.DOWN_LEFT: (2, 0),
            POVDirection.LEFT: (1, 0),
            POVDirection.UP_LEFT: (0, 0),
            POVDirection.NONE: (1, 1),  # Center
        }

        # Create labels for each direction
        for direction, (row, col) in pov_positions.items():
            label = QLabel()
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFixedSize(square_size, square_size)
            label.setObjectName("ButtonInputStateBoxInactive")
            self.grid.addWidget(label, row, col)
            self.pov_labels[direction] = label

    def set_pov_state(self, direction: POVDirection):
        """Update the POV grid to highlight the active direction."""
        for d, label in self.pov_labels.items():
            label.setObjectName("ButtonInputStateBoxActive" if d == direction else "ButtonInputStateBoxInactive")
            self.style().polish(label)


class JoystickStateWidget(QWidget):
    def __init__(self, joystick: RawLocalJoystickDevice | None = None):
        super().__init__()
        self.joystick = joystick
        self.max_axes = 8
        self.axis_bars = []
        self.axis_widgets = []
        self.init_ui()

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_state)
        self.update_timer.start(100)

    def init_ui(self):
        layout = QHBoxLayout()
        layout.setSpacing(10)
        self.setLayout(layout)

        self.button_grid = ButtonGridWidget()
        layout.addWidget(self.button_grid)

        self.axes_group = QGroupBox("Axes")
        axes_layout = QVBoxLayout()
        axes_layout.setSpacing(4)
        self.axes_group.setLayout(axes_layout)

        for _ in range(self.max_axes):
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(50)
            bar.setTextVisible(False)
            bar.setFixedHeight(20)
            self.axis_bars.append(bar)
            self.axis_widgets.append(bar)
            axes_layout.addWidget(bar)

        layout.addWidget(self.axes_group)
        self.pov_grid = POVGridWidget()
        layout.addWidget(self.pov_grid)

    def set_joystick(self, joystick: RawLocalJoystickDevice | None):
        self.joystick = joystick
        self.update_state()

    def update_state(self):
        if not self.joystick or not self.joystick.is_connected():
            self.button_grid.set_button_count(0)
            for widget in self.axis_widgets:
                widget.setVisible(False)
            self.pov_grid.set_pov_state(POVDirection.NONE)
            return

        if self.joystick.is_connected():
            # Buttons
            button_count = self.joystick.get_button_count()
            self.button_grid.set_button_count(button_count)
            for i in range(button_count):
                state = self.joystick.get_button_state(i)
                self.button_grid.set_button_state(i, state)

            # Axes
            axes = self.joystick.get_axes(precision=2)
            for i, value in enumerate(axes):
                if i < self.max_axes:
                    self.axis_widgets[i].setVisible(True)
                    progress_value = int((value + 1.0) * 50)
                    self.axis_bars[i].setValue(progress_value)
            for i in range(len(axes), self.max_axes):
                self.axis_widgets[i].setVisible(False)

            # POV/D-pad
            pov = self.joystick.get_pov_direction()
            self.pov_grid.set_pov_state(pov)
        else:
            self.button_grid.set_button_count(0)
            for widget in self.axis_widgets:
                widget.setVisible(False)
            self.pov_grid.set_pov_state(POVDirection.NONE)


class ControlConsoleControllersTab(QWidget):
    MAX_CONTROLLERS = 8

    def __init__(self):
        super().__init__()
        self.logger = Logger()

        self.root_layout = QHBoxLayout()
        self.setLayout(self.root_layout)

        self.selector_layout = QVBoxLayout()
        self.selector = QListWidget()
        self.selector.setMaximumWidth(250)
        self.selector.setItemDelegate(ActiveItemDelegate())
        self.selector.currentItemChanged.connect(self.on_selection_changed)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.update_controller_list)

        self.selector_layout.addWidget(self.selector)
        self.selector_layout.addWidget(self.refresh_button)
        self.selector_layout.addStretch()

        self.controllers = {}
        self.button_states = {}
        self.selected_index = None

        self.content_stack = QStackedWidget()

        self.no_controller_widget = QFrame()
        no_controller_layout = QVBoxLayout(self.no_controller_widget)
        no_controller_layout.addStretch()
        label = QLabel("No controller selected\nConnect a controller or select one from the list")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        no_controller_layout.addWidget(label)
        no_controller_layout.addStretch()

        self.details_widget = QWidget()
        details_layout = QHBoxLayout(self.details_widget)
        self.state_widget = JoystickStateWidget()
        details_layout.addWidget(self.state_widget)
        details_layout.addStretch()

        # Add widgets to QStackedWidget
        self.content_stack.addWidget(self.no_controller_widget)  # index 0
        self.content_stack.addWidget(self.details_widget)  # index 1
        self.content_stack.setCurrentIndex(0)  # default to "no controller"

        self.root_layout.addLayout(self.selector_layout)
        self.root_layout.addWidget(self.content_stack, stretch=1)

        self.update_controller_list()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_controller_list)
        self.timer.start(2000)

    def update_controller_list(self):
        joystick_names = LocalJoystickIdentifiers.get_names()
        valid_indices = list(range(len(joystick_names)))

        for index in list(self.controllers.keys()):
            if index not in valid_indices:
                self.controllers[index].stop()
                del self.controllers[index]
                self.button_states.pop(index, None)

        self.selector.blockSignals(True)
        try:
            prev_selected_index = self.selected_index

            self.selector.clear()

            index_to_row_map = {}
            selected_row = None

            for i, index in enumerate(valid_indices):
                if index not in self.controllers:
                    try:
                        joystick = RawLocalJoystickDevice(index)
                        joystick.start_polling()
                        self.controllers[index] = joystick
                        self.button_states[index] = [False] * 32
                        for button in range(32):
                            joystick.register_button_callback(
                                button, partial(self.on_button_state_changed, index, button)
                            )
                    except JoystickMissingException as e:
                        self.logger.error(f"Failed to initialize joystick {index}: {e}")
                        continue

                is_any_pressed = any(self.button_states.get(index, [False] * 32))
                item = QListWidgetItem(f"{index}: {joystick_names[index]}")
                item.setData(Qt.ItemDataRole.UserRole + 1, is_any_pressed)
                self.selector.addItem(item)
                index_to_row_map[index] = i

                if index == prev_selected_index:
                    selected_row = i

            if selected_row is not None:
                self.selector.setCurrentRow(selected_row)
            else:
                self.state_widget.set_joystick(None)
                self.content_stack.setCurrentWidget(self.no_controller_widget)
        finally:
            self.selector.blockSignals(False)
            self.update_state_display()

    def on_button_state_changed(self, controller_index: int, button_index: int, state: bool):
        self.button_states.setdefault(controller_index, [False] * 32)
        self.button_states[controller_index][button_index] = state
        is_any_pressed = any(self.button_states[controller_index])
        for row in range(self.selector.count()):
            item = self.selector.item(row)
            index = int(item.text().split(":")[0])
            if index == controller_index:
                item.setData(Qt.ItemDataRole.UserRole + 1, is_any_pressed)
                break

    def update_item_colors(self):
        for row in range(self.selector.count()):
            item = self.selector.item(row)
            index = int(item.text().split(":")[0])
            item.setData(Qt.ItemDataRole.UserRole + 1, self.button_states.get(index, False))

    def on_selection_changed(self, current: QListWidgetItem, _: QListWidgetItem):
        if current:
            self.selected_index = int(current.text().split(":")[0])
        else:
            self.selected_index = None
        self.update_state_display()

    def update_state_display(self):
        selected_item = self.selector.currentItem()
        if selected_item:
            index = int(selected_item.text().split(":")[0])
            self.state_widget.set_joystick(self.controllers.get(index))
            self.content_stack.setCurrentWidget(self.details_widget)
        else:
            self.state_widget.set_joystick(None)
            self.content_stack.setCurrentWidget(self.no_controller_widget)

    @override
    def closeEvent(self, event):
        self.timer.stop()
        for joystick in self.controllers.values():
            joystick.stop()
        self.controllers.clear()
        self.button_states.clear()
        super().closeEvent(event)
