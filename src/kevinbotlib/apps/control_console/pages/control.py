from collections.abc import Callable
from enum import Enum
from typing import Any

from PySide6.QtCore import QItemSelection, Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from kevinbotlib.comm import (
    AnyListSendable,
    BooleanSendable,
    CommPath,
    CommunicationClient,
    StringSendable,
)


class AppState(Enum):
    NO_COMMS = "Communication\nDown"
    WAITING = "Communication\nWaiting"
    CODE_ERROR = "Robot Code\nError"
    ROBOT_DISABLED = "{0}\nDisabled"
    ROBOT_ENABLED = "{0}\nEnabled"


class StateManager:
    def __init__(self, state: AppState, updated: Callable[[AppState], Any]) -> None:
        self._state: AppState = state
        self._updated: Callable[[AppState], Any] = updated

    def set(self, state: AppState):
        self._state = state
        self._updated(state)

    def get(self) -> AppState:
        return self._state


class ControlConsoleControlTab(QWidget):
    def __init__(self, client: CommunicationClient, status_key: str, request_key: str):
        super().__init__()

        self.client = client

        self.status_key = status_key
        self.request_key = request_key

        self.client.add_hook(
            CommPath(self.status_key) / "opmodes",
            AnyListSendable,
            self.on_opmodes_update,
        )
        self.client.add_hook(CommPath(self.status_key) / "opmode", StringSendable, self.on_opmode_update)
        self.client.add_hook(
            CommPath(self.status_key) / "enabled",
            BooleanSendable,
            self.on_enabled_update,
        )

        self.opmodes = []
        self.opmode = None
        self.enabled = None

        self.state = StateManager(AppState.NO_COMMS, self.state_update)
        self.dependencies = [
            lambda: self.client.is_connected(),
            lambda: len(self.opmodes) > 0,
            lambda: self.opmode is not None,
            lambda: self.enabled is not None,
        ]

        self.state_label_timer = QTimer()
        self.state_label_timer.timeout.connect(self.pulse_state_label)
        self.state_label_timer_runs = 0

        self.depencency_periodic = QTimer()
        self.depencency_periodic.setInterval(1000)
        self.depencency_periodic.timeout.connect(self.periodic_dependency_check)
        self.depencency_periodic.start()

        root_layout = QHBoxLayout()
        self.setLayout(root_layout)

        self.opmode_selector = QListWidget()
        self.opmode_selector.setMaximumWidth(200)
        self.opmode_selector.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.opmode_selector.setSelectionBehavior(QListWidget.SelectionBehavior.SelectItems)
        self.opmode_selector.selectionChanged = self.opmode_selection_changed
        root_layout.addWidget(self.opmode_selector)

        self.enable_layout = QGridLayout()
        root_layout.addLayout(self.enable_layout)

        self.enable_button = QPushButton("Enable")
        self.enable_button.setObjectName("EnableButton")
        self.enable_button.setFixedHeight(80)
        self.enable_button.clicked.connect(self.enable_request)
        self.enable_layout.addWidget(self.enable_button, 0, 0, 1, 2)

        self.disable_button = QPushButton("Disable")
        self.disable_button.setObjectName("DisableButton")
        self.disable_button.setFixedHeight(80)
        self.disable_button.setShortcut("Return")
        self.disable_button.clicked.connect(self.disable_request)
        self.enable_layout.addWidget(self.disable_button, 0, 2, 1, 3)

        self.estop_button = QPushButton("EMERGENCY STOP")
        self.estop_button.setObjectName("EstopButton")
        self.estop_button.setFixedHeight(96)
        self.estop_button.setShortcut("Space")
        self.estop_button.pressed.connect(self.estop_request)
        self.enable_layout.addWidget(self.estop_button, 1, 0, 1, 5)

        root_layout.addSpacing(32)

        self.robot_state = QLabel("Communication\nDown")
        self.robot_state.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.robot_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root_layout.addWidget(self.robot_state)

        root_layout.addSpacing(32)

        self.logs_layout = QVBoxLayout()
        root_layout.addLayout(self.logs_layout)

        self.logs = QTextEdit(readOnly=True)
        self.logs.document().setMaximumBlockCount(10000)  # limit log length
        self.logs.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.logs.setObjectName("LogView")

        log_controls_layout = QHBoxLayout()
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.logs.clear)
        log_controls_layout.addWidget(self.clear_button)

        self.autoscroll_checkbox = QCheckBox("Autoscroll")
        self.autoscroll_checkbox.setChecked(True)
        log_controls_layout.addWidget(self.autoscroll_checkbox)

        log_controls_layout.addStretch()

        self.logs_layout.addLayout(log_controls_layout)
        self.logs_layout.addWidget(self.logs)

    def pulse_state_label(self):
        if self.state_label_timer_runs == 3:  # noqa: PLR2004
            self.state_label_timer_runs = 0
            self.state_label_timer.stop()
            self.robot_state.setStyleSheet("font-size: 20px; font-weight: bold;")
            return
        if self.robot_state.styleSheet() == "font-size: 20px; font-weight: bold; color: #f44336;":
            self.robot_state.setStyleSheet("font-size: 20px; font-weight: bold;")
        else:
            self.robot_state.setStyleSheet("font-size: 20px; font-weight: bold; color: #f44336;")
        self.state_label_timer_runs += 1

    def state_update(self, state: AppState):
        self.robot_state.setText(state.value.format(self.opmode))
        if self.opmode in self.opmodes:
            self.opmode_selector.setCurrentRow(self.opmodes.index(self.opmode))

    def opmode_selection_changed(self, _: QItemSelection, __: QItemSelection, /):
        if len(self.opmode_selector.selectedItems()) == 1:
            self.client.send(
                CommPath(self.request_key) / "opmode",
                StringSendable(value=self.opmode_selector.selectedItems()[0].data(0)),
            )

    def enable_request(self):
        if not self.client.is_connected():
            self.state_label_timer.start(100)
            return

        self.client.send(CommPath(self.request_key) / "enabled", BooleanSendable(value=True))

    def disable_request(self):
        if not self.client.is_connected():
            self.state_label_timer.start(100)
            return

        self.client.send(CommPath(self.request_key) / "enabled", BooleanSendable(value=False))

    def estop_request(self):
        if not self.client.is_connected():
            self.state_label_timer.start(100)
            # return
            # don't return - maybe something went wrong with is_connected and estop is still possible

        self.client.send(CommPath(self.request_key) / "estop", BooleanSendable(value=True))

    def on_opmodes_update(self, _: str, sendable: AnyListSendable | None):  # these are for non-initial updates
        if not sendable:
            self.opmode_selector.clear()
            return
        if sendable.value != self.opmodes:
            self.opmodes.clear()
            self.opmode_selector.clear()
            for opmode in sendable.value:
                self.opmode_selector.addItem(opmode)
                self.opmodes.append(opmode)
        # check dependencies
        ready = True
        for cond in self.dependencies:
            if not cond():
                ready = False
                break
        if ready:
            self.state.set(AppState.ROBOT_ENABLED if self.enabled else AppState.ROBOT_DISABLED)

    def on_opmode_update(self, _: str, sendable: StringSendable | None):  # these are for non-initial updates
        if not sendable:
            return
        if sendable.value in self.opmodes:
            self.opmode_selector.setCurrentRow(self.opmodes.index(sendable.value))
            self.opmode = sendable.value
        # check dependencies
        ready = True
        for cond in self.dependencies:
            if not cond():
                ready = False
                break
        if ready:
            self.state.set(AppState.ROBOT_ENABLED if self.enabled else AppState.ROBOT_DISABLED)

    def on_enabled_update(self, _: str, sendable: BooleanSendable | None):
        if not sendable:
            return
        self.enabled = sendable.value
        ready = True
        for cond in self.dependencies:
            if not cond():
                ready = False
                break
        if ready:
            self.state.set(AppState.ROBOT_ENABLED if self.enabled else AppState.ROBOT_DISABLED)

    def periodic_dependency_check(self):
        ready = True
        for cond in self.dependencies:
            if not cond():
                ready = False
                break
        if ready:
            self.state.set(AppState.ROBOT_ENABLED if self.enabled else AppState.ROBOT_DISABLED)

    def clear_opmodes(self):
        self.opmodes.clear()
        self.opmode_selector.clear()
