from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QWidget,
    QStyledItemDelegate, QVBoxLayout, QLabel, QGridLayout, QSizePolicy,
    QGroupBox, QProgressBar
)

from kevinbotlib.joystick import LocalJoystickIdentifiers, RawLocalJoystickDevice, POVDirection
from kevinbotlib.ui.delegates import NoFocusDelegate

ActiveRole = Qt.ItemDataRole.UserRole + 1

class ActiveItemDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index):
        is_active = index.data(ActiveRole)
        if is_active:
            painter.fillRect(option.rect, QColor("green"))
        super().paint(painter, option, index)

class ButtonGridWidget(QGroupBox):
    """Widget displaying a grid of button states as colored squares."""
    def __init__(self, max_buttons: int = 32):
        super().__init__("Buttons")
        self.max_buttons = max_buttons
        self.button_count = 0
        self.button_labels = []
        self.init_ui()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def init_ui(self):
        self.root_layout = QGridLayout()
        self.root_layout.setSpacing(5)
        self.setLayout(self.root_layout)

        square_size = 12
        for i in range(self.max_buttons):
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
            self.button_labels[button_id].setObjectName("ButtonInputStateBoxActive" if state else "ButtonInputStateBoxInactive")
            self.style().polish(self.button_labels[button_id])

    def update_grid_layout(self):
        if self.button_count == 0:
            return
        for i in range(self.button_count):
            row = i % 8
            col = i // 8
            self.root_layout.addWidget(self.button_labels[i], row, col)

class POVGridWidget(QGroupBox):
    """Widget displaying POV/D-pad states in a 3x3 grid."""
    def __init__(self):
        super().__init__("POV")
        self.pov_labels = {}
        self.init_ui()

    def init_ui(self):
        self.root_layout = QGridLayout()
        self.root_layout.setSpacing(5)
        self.setLayout(self.root_layout)

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
            POVDirection.NONE: (1, 1)  # Center
        }

        # Create labels for each direction
        for direction, (row, col) in pov_positions.items():
            label = QLabel()
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFixedSize(square_size, square_size)
            label.setObjectName("ButtonInputStateBoxInactive")
            self.root_layout.addWidget(label, row, col)
            self.pov_labels[direction] = label

    def set_pov_state(self, direction: POVDirection):
        """Update the POV grid to highlight the active direction."""
        for dir, label in self.pov_labels.items():
            label.setObjectName("ButtonInputStateBoxActive" if dir == direction else "ButtonInputStateBoxInactive")
            self.style().polish(label)

class JoystickStateWidget(QWidget):
    """Custom widget to display the state of a joystick with progress bars for axes and POV grid."""
    def __init__(self, joystick: RawLocalJoystickDevice | None = None):
        super().__init__()
        self.joystick = joystick
        self.max_axes = 8
        self.axis_bars: list[QProgressBar] = []
        self.axis_widgets: list[QWidget] = []
        self.init_ui()
        
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_state)
        self.update_timer.start(100)

    def init_ui(self):
        layout = QHBoxLayout()
        self.setLayout(layout)

        # Buttons grid
        self.button_grid = ButtonGridWidget(max_buttons=32)
        layout.addWidget(self.button_grid)

        # Axes group
        self.axes_group = QGroupBox("Axes")
        axes_layout = QVBoxLayout()
        self.axes_group.setLayout(axes_layout)

        for i in range(self.max_axes):
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setValue(50)
            progress.setTextVisible(False)
            progress.setFixedHeight(12)
            progress.setObjectName("AxesStateInputBar")

            self.axis_bars.append(progress)
            self.axis_widgets.append(progress)
            axes_layout.addWidget(progress)

        layout.addWidget(self.axes_group)

        # POV grid
        self.pov_grid = POVGridWidget()
        layout.addWidget(self.pov_grid)

        layout.addStretch()

    def set_joystick(self, joystick: RawLocalJoystickDevice | None):
        self.joystick = joystick
        self.update_state()

    def update_state(self):
        if not self.joystick or not self.joystick._sdl_joystick:
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

    def closeEvent(self, event):
        self.update_timer.stop()
        super().closeEvent(event)


class ControlConsoleControllersTab(QWidget):
    def __init__(self):
        super().__init__()
        root_layout = QHBoxLayout()
        self.setLayout(root_layout)

        self.selector = QListWidget()
        self.selector.setMaximumWidth(200)
        self.selector.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.selector.setSelectionBehavior(QListWidget.SelectionBehavior.SelectItems)
        self.selector.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.selector.setItemDelegate(ActiveItemDelegate())
        self.selector.currentItemChanged.connect(self.on_selection_changed)

        self.controllers = {}
        self.button_states = {}

        self.details_widget = QWidget()
        details_layout = QHBoxLayout()
        self.details_widget.setLayout(details_layout)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.update_controller_list)
        details_layout.addWidget(self.refresh_button)

        details_layout.addStretch()
        
        self.state_widget = JoystickStateWidget()
        details_layout.addWidget(self.state_widget)

        details_layout.addStretch()

        root_layout.addWidget(self.selector)
        root_layout.addWidget(self.details_widget)

        self.update_controller_list()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_controller_list)
        self.timer.start(2000)

    def update_controller_list(self):
        current_selection = self.selector.currentRow()
        self.selector.clear()

        joystick_names = LocalJoystickIdentifiers.get_names()
        self.joystick_guids = LocalJoystickIdentifiers.get_guids()

        for index in joystick_names.keys():
            if index not in self.controllers:
                joystick = RawLocalJoystickDevice(index)
                joystick.start_polling()
                for button in range(32):
                    joystick.register_button_callback(
                        button,
                        lambda state, idx=index: self.on_button_state_changed(idx, state)
                    )
                self.controllers[index] = joystick

        for index in list(self.controllers.keys()):
            if index not in joystick_names:
                self.controllers[index].stop()
                del self.controllers[index]
                if index in self.button_states:
                    del self.button_states[index]

        for index, name in joystick_names.items():
            item = QListWidgetItem(f"{index}: {name}")
            self.selector.addItem(item)

        if current_selection >= 0 and current_selection < self.selector.count():
            self.selector.setCurrentRow(current_selection)
        elif self.selector.count() > 0:
            self.selector.setCurrentRow(0)

        self.update_item_colors()
        self.update_state_display()

    def on_button_state_changed(self, index: int, state: bool):
        if state:
            self.button_states[index] = True
        elif index in self.controllers and not any(self.controllers[index].get_button_state(btn) for btn in range(32)):
            self.button_states[index] = False
        self.update_item_colors()

    def update_item_colors(self):
        for row in range(self.selector.count()):
            item = self.selector.item(row)
            index = int(item.text().split(":")[0])
            item.setData(ActiveRole, self.button_states.get(index, False))

    def on_selection_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        self.update_state_display()

    def update_state_display(self):
        selected_item = self.selector.currentItem()
        if selected_item:
            index = int(selected_item.text().split(":")[0])
            self.state_widget.set_joystick(self.controllers.get(index))
        else:
            self.state_widget.set_joystick(None)

    def closeEvent(self, event):
        self.timer.stop()
        for joystick in self.controllers.values():
            joystick.stop()
        self.controllers.clear()
        self.button_states.clear()
        self.state_widget.close()
        super().closeEvent(event)
