import json
from enum import StrEnum
from functools import partial
from typing import override

import qtawesome
from PySide6.QtCore import QSettings, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QComboBox,
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
    QSpinBox,
    QStackedWidget,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from kevinbotlib.apps.common.widgets import QWidgetList
from kevinbotlib.apps.control_console.components.named_reference import (
    NamedDefaultAxisMapWidget,
    NamedDefaultButtonMapWidget,
)
from kevinbotlib.exceptions import JoystickMissingException
from kevinbotlib.joystick import (
    ControllerMap,
    LocalJoystickIdentifiers,
    POVDirection,
    RawLocalJoystickDevice,
)
from kevinbotlib.logger import Logger


class ActiveItemDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index):
        is_active = index.data(Qt.ItemDataRole.UserRole + 1)
        if is_active:
            painter.fillRect(option.rect, QColor("green"))  # type: ignore
        super().paint(painter, option, index)


class ButtonGridWidget(QGroupBox):
    def __init__(self, max_buttons: int = 32, name: str = "Buttons"):
        super().__init__(name)
        self.max_buttons = max_buttons
        self.button_count = 0
        self.button_labels = []
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.root_layout = QGridLayout()
        self.root_layout.setSpacing(0)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.root_layout)

        square_size = 16
        for i in range(self.max_buttons):
            label = QLabel(str(i), parent=self)
            label.setContentsMargins(0, 0, 0, 0)

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


class ControllerMapType(StrEnum):
    AxisMap = "AxisMap"
    ButtonMap = "ButtonMap"


class ControllerMapEditWidget(QFrame):
    type_changed = Signal(ControllerMapType)
    source_changed = Signal(int)
    destination_changed = Signal(int)
    delete_button_clicked = Signal()

    def __init__(self, kind: ControllerMapType = ControllerMapType.ButtonMap, source: int = 0, dest: int = 0):
        super().__init__()
        self.setFrameShape(QFrame.Shape.Panel)

        self.root_layout = QHBoxLayout()
        self.root_layout.setContentsMargins(2, 2, 2, 2)
        self.setLayout(self.root_layout)

        self.type_selector = QComboBox()
        for load_kind in ControllerMapType:
            self.type_selector.addItem(load_kind.name)
        self.type_selector.setCurrentText(kind.name)
        self.type_selector.currentTextChanged.connect(lambda x: self.type_changed.emit(ControllerMapType(x)))
        self.root_layout.addWidget(self.type_selector)

        self.root_layout.addStretch()

        self.source_selector = QSpinBox(minimum=0, maximum=255, value=source)
        self.source_selector.valueChanged.connect(lambda x: self.source_changed.emit(x))
        self.root_layout.addWidget(self.source_selector)

        arrow = qtawesome.IconWidget()
        arrow.setIconSize(QSize(16, 16))
        arrow.setIcon(qtawesome.icon("mdi6.arrow-right-thick"))
        arrow.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.root_layout.addWidget(arrow)

        self.destination_selector = QSpinBox(minimum=0, maximum=255, value=dest)
        self.destination_selector.valueChanged.connect(lambda x: self.destination_changed.emit(x))
        self.root_layout.addWidget(self.destination_selector)

        self.delete_button = QPushButton()
        self.delete_button.setIcon(qtawesome.icon("mdi6.delete-forever", color="#d45b5a"))
        self.delete_button.setIconSize(QSize(24, 24))
        self.delete_button.setFixedSize(QSize(32, 32))
        self.delete_button.clicked.connect(self.delete_button_clicked.emit)
        self.root_layout.addWidget(self.delete_button)


class MapEditor(QGroupBox):
    def __init__(self, settings: QSettings, joystick: RawLocalJoystickDevice | None):
        super().__init__("Map Editor")
        self.guid = joystick.guid if joystick else ""
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.settings = settings
        self.joystick = joystick

        self.root_layout = QVBoxLayout()
        self.setLayout(self.root_layout)

        self.guid_label = QLabel("GUID: Unknown")
        self.root_layout.addWidget(self.guid_label)

        self.list = QWidgetList()
        self.list.setMinimumWidth(320)
        self.root_layout.addWidget(self.list)

        self.maps: list[ControllerMapEditWidget] = []

        self.add_map_button = QPushButton("Add Map")
        self.add_map_button.clicked.connect(self.add_map)
        self.root_layout.addWidget(self.add_map_button)

        self.info = QLabel("Maps are automatically saved and GUID-linked")
        self.root_layout.addWidget(self.info)

    def add_map(self):
        cmap = ControllerMapEditWidget()
        cmap.delete_button_clicked.connect(partial(self.remove_map, cmap))
        cmap.source_changed.connect(self.save_map)
        cmap.destination_changed.connect(self.save_map)
        cmap.type_changed.connect(self.save_map)
        self.maps.append(cmap)
        self.list.add_widget(cmap)
        self.save_map()

    def remove_map(self, cmap: ControllerMapEditWidget):
        self.maps.remove(cmap)
        self.list.remove_widget(cmap)
        self.save_map()

    def save_map(self):
        if self.guid:
            self.settings.setValue(f"controllers.map.{self.guid}", json.dumps(self.get_joystick_map().__dict__))
        else:
            Logger().warning("Couldn't save controller map: GUID is not valid")
        if self.joystick:
            self.joystick.apply_map(self.get_joystick_map())

    def _apply_map(self, cmap: dict, kind: ControllerMapType):
        for source, dest in cmap.items():
            widget = ControllerMapEditWidget(kind, source, dest)
            widget.delete_button_clicked.connect(partial(self.remove_map, widget))
            widget.source_changed.connect(self.save_map)
            widget.destination_changed.connect(self.save_map)
            widget.type_changed.connect(self.save_map)
            self.maps.append(widget)
            self.list.add_widget(widget)

    def load_map(self, cmap: ControllerMap):
        self.list.clear_widgets()
        self._apply_map(cmap.button_map, ControllerMapType.ButtonMap)
        self._apply_map(cmap.axis_map, ControllerMapType.AxisMap)

    def get_joystick_map(self) -> ControllerMap:
        return ControllerMap(
            button_map={
                map_item.source_selector.value(): map_item.destination_selector.value()
                for map_item in self.maps
                if map_item.type_selector.currentText() == ControllerMapType.ButtonMap.name
            },
            axis_map={
                map_item.source_selector.value(): map_item.destination_selector.value()
                for map_item in self.maps
                if map_item.type_selector.currentText() == ControllerMapType.AxisMap.name
            },
        )

    def update_guid(self, guid: str):
        self.guid_label.setText(f"GUID: {guid}")
        if self.guid != guid:
            value = self.settings.value(  # type: ignore
                f"controllers.map.{guid}",
                type=str,
            )
            self.load_map(ControllerMap(**json.loads(value)) if value else ControllerMap(button_map={}, axis_map={}))  # type: ignore
        self.guid = guid


class JoystickStateWidget(QWidget):
    def __init__(self, settings: QSettings, joystick: RawLocalJoystickDevice | None = None):
        super().__init__()
        self.setContentsMargins(0, 0, 0, 0)

        self.joystick = joystick
        self.max_axes = 8
        self.mapped_axis_bars = []
        self.mapped_axis_widgets = []
        self.raw_axis_bars = []
        self.raw_axis_widgets = []

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_state)
        self.update_timer.start(100)

        layout = QHBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.raw_button_grid = ButtonGridWidget(name="Raw Btn")
        layout.addWidget(self.raw_button_grid)

        self.mapped_button_grid = ButtonGridWidget(name="Map Btn")
        layout.addWidget(self.mapped_button_grid)

        self.raw_axes_group = QGroupBox("Raw Axes")
        raw_axes_layout = QVBoxLayout()
        raw_axes_layout.setSpacing(4)
        self.raw_axes_group.setLayout(raw_axes_layout)

        for _ in range(self.max_axes):
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(50)
            bar.setTextVisible(False)
            bar.setFixedHeight(20)
            self.raw_axis_widgets.append(bar)
            raw_axes_layout.addWidget(bar)

        self.mapped_axes_group = QGroupBox("Mapped Axes")
        mapped_axes_layout = QVBoxLayout()
        mapped_axes_layout.setSpacing(4)
        self.mapped_axes_group.setLayout(mapped_axes_layout)

        for _ in range(self.max_axes):
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(50)
            bar.setTextVisible(False)
            bar.setFixedHeight(20)
            self.mapped_axis_bars.append(bar)
            self.mapped_axis_widgets.append(bar)
            mapped_axes_layout.addWidget(bar)

        layout.addWidget(self.raw_axes_group)
        layout.addWidget(self.mapped_axes_group)
        self.pov_grid = POVGridWidget()
        layout.addWidget(self.pov_grid)

        self.map_editor = MapEditor(settings, joystick)
        layout.addWidget(self.map_editor, 2)

        button_reference = NamedDefaultButtonMapWidget()
        layout.addWidget(button_reference)

        axis_reference = NamedDefaultAxisMapWidget()
        layout.addWidget(axis_reference)

    def set_joystick(self, joystick: RawLocalJoystickDevice | None):
        self.joystick = joystick
        self.map_editor.joystick = joystick
        self.update_state()

    def update_state(self):
        if not self.joystick or not self.joystick.is_connected():
            self.raw_button_grid.set_button_count(0)
            self.mapped_button_grid.set_button_count(0)
            for widget in self.mapped_axis_widgets:
                widget.setVisible(False)
            self.pov_grid.set_pov_state(POVDirection.NONE)
            return

        if self.joystick.is_connected():
            # Map Editor
            self.map_editor.update_guid("".join(f"{b:02x}" for b in self.joystick.guid))

            # Buttons
            button_count = self.joystick.get_button_count()
            self.raw_button_grid.set_button_count(button_count)
            self.mapped_button_grid.set_button_count(button_count)
            for i in range(button_count):
                state = self.joystick.get_button_state(i)
                self.mapped_button_grid.set_button_state(i, state)

                # reverse the controller map
                cmap = self.joystick.controller_map.button_map
                reversed_button = i if i not in cmap.values() else list(cmap.keys())[list(cmap.values()).index(i)]

                self.raw_button_grid.set_button_state(i, self.joystick.get_button_state(reversed_button))

            # Axes
            axes = self.joystick.get_axes(precision=2)
            for i, value in enumerate(axes):
                if i < self.max_axes:
                    self.mapped_axis_widgets[i].setVisible(True)
                    progress_value = int((value + 1.0) * 50)
                    self.mapped_axis_bars[i].setValue(progress_value)

                    # reverse the controller map
                    cmap = self.joystick.controller_map.axis_map
                    reversed_axis = i if i not in cmap.values() else list(cmap.keys())[list(cmap.values()).index(i)]
                    progress_value = int((self.joystick.get_axes(precision=2)[reversed_axis] + 1.0) * 50)
                    self.raw_axis_widgets[i].setValue(progress_value)

            for i in range(len(axes), self.max_axes):
                self.mapped_axis_widgets[i].setVisible(False)
                self.raw_axis_widgets[i].setVisible(False)

            # POV/D-pad
            pov = self.joystick.get_pov_direction()
            self.pov_grid.set_pov_state(pov)
        else:
            self.raw_button_grid.set_button_count(0)
            for widget in self.mapped_axis_widgets:
                widget.setVisible(False)
            self.pov_grid.set_pov_state(POVDirection.NONE)


class ControlConsoleControllersTab(QWidget):
    MAX_CONTROLLERS = 8

    def __init__(self, settings: QSettings):
        super().__init__()

        self.settings = settings
        self.logger = Logger()

        self.root_layout = QHBoxLayout()
        self.setLayout(self.root_layout)

        self.selector_layout = QVBoxLayout()
        self.selector = QListWidget()
        self.selector.setMaximumWidth(250)
        self.selector.setMinimumWidth(200)
        self.selector.setItemDelegate(ActiveItemDelegate())
        self.selector.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.selector.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.selector.model().rowsMoved.connect(self.on_controller_reordered)
        self.selector.currentItemChanged.connect(self.on_selection_changed)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.update_controller_list)

        self.selector_layout.addWidget(self.selector)
        self.selector_layout.addWidget(self.refresh_button)

        self.controllers: dict[int, RawLocalJoystickDevice] = {}
        self.button_states_raw = {}
        self.button_states_mapped = {}
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

        self.state_widget = JoystickStateWidget(settings)
        details_layout.addWidget(self.state_widget)

        # Add widgets to QStackedWidget
        self.content_stack.addWidget(self.no_controller_widget)  # index 0
        self.content_stack.addWidget(self.details_widget)  # index 1
        self.content_stack.setCurrentIndex(0)  # default to "no controller"

        self.root_layout.addLayout(self.selector_layout)
        self.root_layout.addWidget(self.content_stack)

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
        self.button_states_raw = {
            index: self.button_states_raw[index] for index in self.controller_order if index in self.button_states_raw
        }
        self.button_states_mapped = {
            index: self.button_states_mapped[index]
            for index in self.controller_order
            if index in self.button_states_mapped
        }

    @property
    def ordered_controllers(self) -> dict:
        return {index: self.controllers[index] for index in self.controller_order if index in self.controllers}

    def update_controller_list(self):
        joystick_names = LocalJoystickIdentifiers.get_names()
        valid_indices = list(range(len(joystick_names)))

        for index in list(self.controllers.keys()):
            if index not in valid_indices:
                self.controllers[index].stop()
                del self.controllers[index]
                self.button_states_raw.pop(index, None)
                self.button_states_mapped.pop(index, None)

        self.selector.blockSignals(True)
        try:
            prev_selected_index = self.selected_index
            previous_order = []
            for i in range(self.selector.count()):
                item = self.selector.item(i)
                previous_order.append(item.text())  # or extract index instead

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

                        # load map
                        value = self.settings.value(  # type: ignore
                            f"controllers.map.{''.join(f'{b:02x}' for b in joystick.guid)}",
                            type=str,
                        )
                        if value:
                            cmap = ControllerMap(**json.loads(value))  # type: ignore
                            joystick.apply_map(cmap)
                        else:
                            Logger().info(f"No controller map present for {joystick.guid}")

                        joystick.start_polling()
                        joystick.rumble(1, 1, 0.25)
                        self.controllers[index] = joystick
                        self.button_states_raw[index] = [False] * 32
                        self.button_states_mapped[index] = [False] * 32
                        for button in range(32):
                            joystick.register_button_callback(
                                button, partial(self.on_button_state_changed, index, button)
                            )
                    except JoystickMissingException as e:
                        self.logger.error(f"Failed to initialize joystick {index}: {e}")
                        continue

                is_any_pressed = any(self.button_states_raw.get(index, [False] * 32))
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
        # reverse the controller map
        cmap = self.controllers[controller_index].controller_map.button_map
        if button_index not in cmap.values():
            reversed_button = button_index
        else:
            reversed_button = list(cmap.keys())[list(cmap.values()).index(button_index)]

        self.button_states_raw.setdefault(controller_index, [False] * 32)
        self.button_states_mapped.setdefault(controller_index, [False] * 32)
        self.button_states_raw[controller_index][reversed_button] = state
        self.button_states_mapped[controller_index][button_index] = state
        is_any_pressed = any(self.button_states_raw[controller_index])
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
            item.setData(Qt.ItemDataRole.UserRole + 1, self.button_states_raw.get(index, False))

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
        self.button_states_raw.clear()
        super().closeEvent(event)
