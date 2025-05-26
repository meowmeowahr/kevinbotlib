from functools import partial
from typing import override

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
    QTextEdit,
)

from kevinbotlib.exceptions import JoystickMissingException
from kevinbotlib.joystick import LocalJoystickIdentifiers, RawLocalJoystickDevice
from kevinbotlib.logger import Logger


class ActiveItemDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index):
        is_active = index.data(Qt.ItemDataRole.UserRole + 1)
        if is_active:
            painter.fillRect(option.rect, QColor("green"))
        super().paint(painter, option, index)


class JoystickStateWidget(QWidget):
    def __init__(self, joystick: RawLocalJoystickDevice | None = None):
        super().__init__()
        self.joystick = joystick
        self.max_axes = 8
        self.axis_bars = []
        self.state_display = QTextEdit()
        self.init_ui()

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_state)
        self.update_timer.start(100)

    def init_ui(self):
        layout = QHBoxLayout()
        layout.setSpacing(10)
        self.setLayout(layout)

        # Large Text Edit for Buttons and POV
        self.state_display.setReadOnly(True)
        self.state_display.setFont(QFont("Monospace", 14))
        layout.addWidget(self.state_display, stretch=2) # Give more space to the text display

        self.axes_group = QGroupBox("Axes")
        axes_layout = QVBoxLayout()
        axes_layout.setSpacing(4)
        self.axes_group.setLayout(axes_layout)

        for i in range(self.max_axes):
            axis_label = QLabel(f"Axis {i}:")
            bar = QProgressBar()
            bar.setRange(-100, 100) # Assuming axis values range from -1 to 1
            bar.setValue(0)
            bar.setTextVisible(True)
            bar.setFixedHeight(20)

            axis_widget_layout = QHBoxLayout()
            axis_widget_layout.addWidget(axis_label)
            axis_widget_layout.addWidget(bar)

            axis_container = QWidget()
            axis_container.setLayout(axis_widget_layout)

            self.axis_bars.append(bar)
            axes_layout.addWidget(axis_container)

        layout.addWidget(self.axes_group, stretch=1)

    def set_joystick(self, joystick: RawLocalJoystickDevice | None):
        self.joystick = joystick
        self.update_state()

    def update_state(self):
        if not self.joystick:
            self.state_display.setText("No joystick connected or selected.")
            for bar in self.axis_bars:
                bar.setValue(0)
            return

        # Update button and POV state in the text edit
        text_output = []
        text_output.append("--- Buttons ---")
        button_states = []
        for i in range(self.joystick.get_button_count()):
            state = self.joystick.get_button_state(i)
            button_states.append(f"B{i}: {'ON' if state else 'OFF'}")
        text_output.append(" ".join(button_states))
        text_output.append("\n--- POV ---")
        pov_direction = self.joystick.get_pov_direction() # Assuming only one POV for simplicity
        pov_text = "POV 0: "
        if pov_direction == -1:
            pov_text += "Centered"
        else:
            pov_text += f"{pov_direction}°"
        text_output.append(pov_text)

        # Set text and apply formatting
        self.state_display.setText("\n".join(text_output))

        # Update Axis bars
        for i in range(self.max_axes):
            if i < self.joystick.get_axis_count():
                print("axes", self.joystick.get_axes())
                value = 0 # Scale to -100 to 100
                self.axis_bars[i].setValue(value)
            else:
                self.axis_bars[i].setValue(0) # Reset if axis doesn't exist


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
        self.selector.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.selector.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.selector.model().rowsMoved.connect(self.on_controller_reordered)
        self.selector.currentItemChanged.connect(self.on_selection_changed)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.update_controller_list)

        self.selector_layout.addWidget(self.selector)
        self.selector_layout.addWidget(self.refresh_button)
        self.selector_layout.addStretch()

        self.controllers = {}
        self.button_states = {} # Keep for the list item active indicator
        self.controller_order = []
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

    def on_controller_reordered(self, _, __, ___, ____, _____):
        new_order = []
        for i in range(self.selector.count()):
            item = self.selector.item(i)
            index = int(item.text().split(":")[0])
            new_order.append(index)

        self.controller_order = new_order

        # Rebuild controllers in new order
        self.controllers = {
            index: self.controllers[index] for index in self.controller_order if index in self.controllers
        }
        self.button_states = {
            index: self.button_states[index] for index in self.controller_order if index in self.button_states
        }

    @property
    def ordered_controllers(self) -> dict:
        return {index: self.controllers[index] for index in self.controller_order if index in self.controllers}

    def update_controller_list(self):
        count = LocalJoystickIdentifiers.get_count()
        print(f"{count} joysticks present")
        joystick_names = LocalJoystickIdentifiers.get_count()
        valid_indices = list(range(joystick_names))

        for index in list(self.controllers.keys()):
            if index not in valid_indices:
                self.controllers[index].stop()
                del self.controllers[index]
                self.button_states.pop(index, None)

        self.selector.blockSignals(True)
        try:
            prev_selected_index = self.selected_index
            previous_order = []
            for i in range(self.selector.count()):
                item = self.selector.item(i)
                previous_order.append(item.text())

            self.selector.clear()

            index_to_row_map = {}
            selected_row = None

            # Preserve existing order or append new indices
            for index in valid_indices:
                if index not in self.controller_order:
                    self.controller_order.append(index)

            # Remove deleted indices
            self.controller_order = [idx for idx in self.controller_order if idx in valid_indices]

            for i, index in enumerate(self.controller_order):
                if index not in self.controllers:
                    try:
                        joystick = RawLocalJoystickDevice(index)
                        joystick.start_polling()
                        self.controllers[index] = joystick
                        # Initialize button states for new joysticks
                        self.button_states[index] = [False] * 32
                        for button in range(32):
                            joystick.register_button_callback(
                                button, partial(self.on_button_state_changed, index, button)
                            )
                    except JoystickMissingException as e:
                        self.logger.error(f"Failed to initialize joystick {index}: {e}")
                        continue

                # Ensure button_states is initialized for the current joystick's button count
                current_joystick_button_count = 32 if index in self.controllers else 0
                if index in self.button_states and len(self.button_states[index]) < current_joystick_button_count:
                    # Extend if the joystick has more buttons than previously tracked
                    self.button_states[index].extend([False] * (current_joystick_button_count - len(self.button_states[index])))
                elif index not in self.button_states:
                    self.button_states[index] = [False] * current_joystick_button_count

                is_any_pressed = any(self.button_states.get(index, [False] * current_joystick_button_count))
                item = QListWidgetItem(f"{index}: {index}")
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
        # Ensure the list is large enough for the button_index
        if controller_index in self.button_states:
            current_button_count = len(self.button_states[controller_index])
            if button_index >= current_button_count:
                # Extend the list with False values if button_index is out of bounds
                self.button_states[controller_index].extend([False] * (button_index - current_button_count + 1))
        else:
            # Initialize with enough False values
            self.button_states[controller_index] = [False] * (button_index + 1)

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
            # Assuming button_states is accurately maintained for each index
            is_any_pressed = any(self.button_states.get(index, [False] * 32))
            item.setData(Qt.ItemDataRole.UserRole + 1, is_any_pressed)

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