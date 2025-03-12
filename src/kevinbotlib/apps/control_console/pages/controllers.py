from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QWidget

from kevinbotlib.joystick import LocalJoystickIdentifiers, RawLocalJoystickDevice
from kevinbotlib.ui.delegates import NoFocusDelegate


class ControlConsoleControllersTab(QWidget):
    def __init__(self):
        super().__init__()

        # Main layout
        root_layout = QHBoxLayout()
        self.setLayout(root_layout)

        # Controller list
        self.selector = QListWidget()
        self.selector.setMaximumWidth(200)
        self.selector.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.selector.setSelectionBehavior(QListWidget.SelectionBehavior.SelectItems)
        self.selector.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.selector.setItemDelegate(NoFocusDelegate())

        # Internal state management
        self.controllers = {}  # Dictionary of index: RawLocalJoystickDevice
        self.button_states = {}  # Track if any button is pressed per controller

        # Right side: Controller details
        self.details_widget = QWidget()

        details_layout = QHBoxLayout()
        self.details_widget.setLayout(details_layout)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.update_controller_list)
        details_layout.addWidget(self.refresh_button)

        details_layout.addStretch()

        # Add widgets to main layout
        root_layout.addWidget(self.selector)
        root_layout.addWidget(self.details_widget)

        # Initial population of controllers
        self.update_controller_list()

        # Set up auto-refresh timer (updates every 2 seconds)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_controller_list)
        self.timer.start(2000)

    def update_controller_list(self):
        """Update the list of connected controllers."""
        current_selection = self.selector.currentRow()
        self.selector.clear()

        # Detect and initialize controllers
        joystick_names = LocalJoystickIdentifiers.get_names()
        self.joystick_guids = LocalJoystickIdentifiers.get_guids()

        # Initialize new controllers and start polling
        for index in joystick_names.keys():
            if index not in self.controllers:
                joystick = RawLocalJoystickDevice(index)
                joystick.start_polling()
                # Register callback for any button (up to 32 buttons assumed)
                for button in range(32):  # Arbitrary max, adjust as needed
                    joystick.register_button_callback(
                        button,
                        lambda state, idx=index: self.on_button_state_changed(idx, state)
                    )
                self.controllers[index] = joystick

        # Remove disconnected controllers
        for index in list(self.controllers.keys()):
            if index not in joystick_names:
                self.controllers[index].stop()
                del self.controllers[index]
                if index in self.button_states:
                    del self.button_states[index]

        # Populate list
        for index, name in joystick_names.items():
            item = QListWidgetItem(f"{index}: {name}")
            if self.button_states.get(index, False):
                item.setBackground(QColor("green"))
            else:
                item.setBackground(QColor("transparent"))
            self.selector.addItem(item)

        # Restore selection if possible
        if current_selection >= 0 and current_selection < self.selector.count():
            self.selector.setCurrentRow(current_selection)
        elif self.selector.count() > 0:
            self.selector.setCurrentRow(0)

    def on_button_state_changed(self, index: int, state: bool):
        """Callback for button state changes."""
        # Update button state (True if any button is pressed)
        if state:
            self.button_states[index] = True
        elif index in self.controllers and not any(self.controllers[index].get_button_state(btn) for btn in range(32)):
            self.button_states[index] = False
        self.update_item_colors()

    def update_item_colors(self):
        """Update the color of list items based on button states."""
        for row in range(self.selector.count()):
            item = self.selector.item(row)
            index = int(item.text().split(":")[0])
            if self.button_states.get(index, False):
                item.setBackground(QColor("green"))
            else:
                item.setBackground(QColor("transparent"))

    def closeEvent(self, event):
        """Clean up when widget is closed."""
        self.timer.stop()
        for joystick in self.controllers.values():
            joystick.stop()
        self.controllers.clear()
        self.button_states.clear()
        super().closeEvent(event)
