import contextlib
import functools
import json
import os
import sys
import time
from dataclasses import dataclass
from queue import Queue
from threading import Thread
from types import TracebackType
from typing import override

import ansi2html
import qtawesome as qta
import superqt.utils
from PySide6.QtCore import (
    QCommandLineOption,
    QCommandLineParser,
    QCoreApplication,
    QItemSelection,
    QModelIndex,
    QObject,
    QPropertyAnimation,
    QRegularExpression,
    QSettings,
    Qt,
    QThread,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QCloseEvent,
    QFont,
    QIcon,
    QRegularExpressionValidator,
    QTextOption,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)
from superqt import QFlowLayout

import kevinbotlib.apps.dashboard.resources_rc
from kevinbotlib.__about__ import __version__
from kevinbotlib.apps.common.abc import ThemableWindow
from kevinbotlib.apps.common.about import AboutDialog
from kevinbotlib.apps.common.settings_rows import Divider, UiColorSettingsSwitcher
from kevinbotlib.apps.common.toast import NotificationWidget, Notifier, Severity
from kevinbotlib.apps.common.widgets import WrapAnywhereLabel
from kevinbotlib.apps.dashboard.card_types import determine_widget_types, item_loader
from kevinbotlib.apps.dashboard.grid import (
    GridGraphicsView,
    WidgetGridController,
)
from kevinbotlib.apps.dashboard.grid_theme import Themes as GridThemes
from kevinbotlib.apps.dashboard.helpers import get_structure_text
from kevinbotlib.apps.dashboard.tree import DictTreeModel
from kevinbotlib.apps.dashboard.widgets.base import WidgetItem
from kevinbotlib.comm import RedisCommClient
from kevinbotlib.logger import Level, Logger, LoggerConfiguration, LoggerWriteOpts
from kevinbotlib.ui.theme import Theme, ThemeStyle
from kevinbotlib.vision import VisionCommUtils


class LatencyWorker(QObject):
    get_latency = Signal()
    latency = Signal(float)

    def __init__(self, client: RedisCommClient):
        super().__init__()
        self.client = client
        self.get_latency.connect(self.get)

    @Slot()
    def get(self):
        latency = self.client.get_latency()
        self.latency.emit(latency)


class WidgetPalette(QWidget):
    def __init__(self, graphics_view, client: RedisCommClient, parent=None):
        super().__init__(parent)

        self.client = client

        self.graphics_view = graphics_view
        self.controller = WidgetGridController(self.graphics_view)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tree = QTreeView()
        self.tree.setHeaderHidden(True)
        layout.addWidget(self.tree, 2)

        self.model = DictTreeModel({})
        self.tree.setModel(self.model)
        self.tree.selectionChanged = self._tree_select

        self.panel = TopicStatusPanel(self.client)
        self.panel.added.connect(self.add_widget)
        layout.addWidget(self.panel, 1)

    def _tree_select(self, selected: QItemSelection, _: QItemSelection):
        self.panel.set_data(selected.indexes()[0].data(Qt.ItemDataRole.UserRole))

    def add_widget(self, widget_info: tuple[type[WidgetItem], str, dict]):
        self.controller.add(
            widget_info[0](
                widget_info[1].split("/")[-1],
                self.panel.current_key if self.panel.current_key else "",
                {},
                self.graphics_view,
                1,
                1,
                self.client,
            )
        )

    def remove_widget(self, widget):
        self.graphics_view.scene().removeItem(widget)


class SettingsWindow(QDialog):
    on_applied = Signal()

    def __init__(self, parent: "Application", settings: QSettings):
        super().__init__(parent=parent)
        self.setModal(True)

        self.settings = settings

        self.root_layout = QVBoxLayout()
        self.setLayout(self.root_layout)

        self.form = QFormLayout()
        self.root_layout.addLayout(self.form)

        self.form.addRow(Divider("Theme"))

        self.form.addRow(
            NotificationWidget(
                "Warning", "A restart is required to fully apply the theme", Severity.Warning.value, 0, bg=False
            )
        )

        self.theme = UiColorSettingsSwitcher(settings, "theme", parent)
        self.form.addRow("Theme", self.theme)

        self.form.addRow(Divider("Grid"))

        self.grid_size = QSpinBox(minimum=8, maximum=256, singleStep=2, value=self.settings.value("grid", 48, int))  # type: ignore
        self.form.addRow("Grid Size", self.grid_size)

        self.grid_rows = QSpinBox(minimum=1, maximum=256, singleStep=2, value=self.settings.value("rows", 10, int))  # type: ignore
        self.form.addRow("Grid Rows", self.grid_rows)

        self.grid_cols = QSpinBox(minimum=1, maximum=256, singleStep=2, value=self.settings.value("cols", 10, int))  # type: ignore
        self.form.addRow("Grid Columns", self.grid_cols)

        self.form.addRow(Divider("Network"))

        self.net_ip = QLineEdit(self.settings.value("ip", "10.0.0.2", str), placeholderText="***.***.***.***")  # type: ignore
        ip_range = "(?:[0-1]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])"
        ip_regex = QRegularExpression("^" + ip_range + "\\." + ip_range + "\\." + ip_range + "\\." + ip_range + "$")
        ip_validator = QRegularExpressionValidator(ip_regex)
        self.net_ip.setValidator(ip_validator)
        self.form.addRow("IP Address", self.net_ip)

        self.net_port = QSpinBox(minimum=1024, maximum=65535, value=self.settings.value("port", 8765, int))  # type: ignore
        self.form.addRow("Port", self.net_port)

        self.form.addRow(Divider("Polling"))

        self.poll_rate = QSpinBox(
            minimum=50,
            maximum=2500,
            singleStep=50,
            value=self.settings.value("rate", 200, int),  # type: ignore
            suffix="ms",
        )
        self.form.addRow("Polling Rate", self.poll_rate)

        self.button_layout = QHBoxLayout()
        self.button_layout.addStretch()
        self.root_layout.addLayout(self.button_layout)

        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply)
        self.button_layout.addWidget(self.apply_button)

        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.close)
        self.button_layout.addWidget(self.exit_button)

    def apply(self):
        self.on_applied.emit()


class TopicStatusPanel(QStackedWidget):
    added = Signal(tuple)

    def __init__(self, client: RedisCommClient):
        super().__init__()
        self.setFrameShape(QFrame.Shape.Panel)

        self.client = client
        self.raw_data = {}
        self.current_key: str | None = None

        self._add_buttons: list[QToolButton] = []  # New: persistent buttons

        # No data widget
        no_data_label = QLabel("Select a topic for more info", alignment=Qt.AlignmentFlag.AlignCenter)
        no_data_label.setContentsMargins(16, 16, 16, 16)
        self.addWidget(no_data_label)

        # Main data widget with tabs
        data_widget = QWidget()
        self.addWidget(data_widget)

        data_layout = QVBoxLayout()
        data_widget.setLayout(data_layout)

        self.data_topic = QLabel()
        self.data_topic.setStyleSheet("font-size: 18px;")
        data_layout.addWidget(self.data_topic)

        data_layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        # Tab widget for switching views
        self.tab_widget = QTabWidget()
        data_layout.addWidget(self.tab_widget)

        # Data view (existing content)
        data_view = QWidget()
        data_view_layout = QVBoxLayout()
        data_view.setLayout(data_view_layout)

        data_view_layout.addStretch()

        self.data_type = QLabel("Data Type: Unknown")
        data_view_layout.addWidget(self.data_type)

        self.data_known = QLabel("Data Compatible: Unknown")
        data_view_layout.addWidget(self.data_known)

        self.value = WrapAnywhereLabel("Value: Dashboard Error")
        self.value.setWordWrap(True)
        self.value.setMinimumWidth(100)
        self.value.setFont(QFont("monospace", self.font().pointSize()))
        data_view_layout.addWidget(self.value)

        data_view_layout.addStretch()

        self.add_layout = QFlowLayout()
        self.add_layout.setSpacing(8)
        data_view_layout.addLayout(self.add_layout)

        data_view_layout.addStretch()

        self.tab_widget.addTab(data_view, "Data View")

        # Raw view
        raw_view = QWidget()
        raw_view_layout = QVBoxLayout()
        raw_view.setLayout(raw_view_layout)

        self.raw_text = QTextEdit()
        self.raw_text.setFont(QFont("monospace", 10))
        self.raw_syntax = superqt.utils.CodeSyntaxHighlight(self.raw_text, "json", "monokai")
        self.raw_text.setReadOnly(True)
        self.raw_text.setWordWrapMode(QTextOption.WrapMode.NoWrap)
        self.raw_text.setPlaceholderText("Raw data will appear here")
        raw_view_layout.addWidget(self.raw_text)

        self.tab_widget.addTab(raw_view, "Raw View")

    def set_data(self, data: str | None):
        if not data:
            self.setCurrentIndex(0)
            self.data_topic.setText("")
            self.data_type.setText("Data Type: Unknown")
            self.data_known.setText("Data Compatible: Unknown")
            self.value.setText("Value: Dashboard Error")
            self.raw_text.setText("")
            self._hide_all_buttons()
            return

        self.setCurrentIndex(1)

        self.data_topic.setText(data)
        self.current_key = data
        raw = self.raw_data.get(data) or self.client.get_raw(data)
        if not raw:
            self._hide_all_buttons()
            return

        self.data_type.setText(f"Data Type: {raw.get('did', 'Unknown')}")
        self.data_known.setText(f"Data Compatible: {raw['did'] in self.client.SENDABLE_TYPES}")
        self.value.setText(f"Value: {get_structure_text(raw)}")

        raw_content = json.dumps(raw, indent=2) if raw else "No raw data available"
        if self.tab_widget.currentIndex() == 1:
            if raw_content != self.raw_text.document().toPlainText():
                vscroll = self.raw_text.verticalScrollBar().value()
                hscroll = self.raw_text.horizontalScrollBar().value()
                self.raw_text.setText(raw_content)
                self.raw_text.verticalScrollBar().setValue(vscroll)
                self.raw_text.horizontalScrollBar().setValue(hscroll)
        elif self.raw_text.toPlainText() != "Raw data will appear here":
            self.raw_text.setText("Raw data will appear here")

        self._update_add_buttons(raw)

    def _hide_all_buttons(self):
        for button in self._add_buttons:
            button.hide()

    def _update_add_buttons(self, raw: dict):
        wt = determine_widget_types(raw["did"])
        if not wt:
            self._hide_all_buttons()
            return

        needed = len(wt)
        # Create more buttons if not enough
        while len(self._add_buttons) < needed:
            button = QToolButton()
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setIcon(qta.icon("mdi6.card-plus"))
            self.add_layout.addWidget(button)
            self._add_buttons.append(button)

        # Update button properties and show them
        for i, (name, wtype) in enumerate(wt.items()):
            button = self._add_buttons[i]
            button.setText(f"Add {name}")
            with contextlib.suppress(TypeError):
                button.pressed.disconnect()  # Prevent duplicate signal connections
            button.pressed.connect(functools.partial(self.added.emit, (wtype, self.current_key, raw)))
            button.show()

        # Hide any extra buttons
        for i in range(len(wt), len(self._add_buttons)):
            self._add_buttons[i].hide()


class PollingWorker(QObject):
    result_ready = Signal(dict, list, list, dict)

    def __init__(self, client: RedisCommClient, model, tree, get_index_path, controller: WidgetGridController):
        super().__init__()
        self.client = client
        self.model = model
        self.tree = tree
        self.controller = controller
        self.get_index_path = get_index_path
        self.running = False

    @Slot()
    def run(self):
        if self.running:
            return

        if not self.client.is_connected():
            return

        self.running = True

        data = {}
        raw_data = self.client.get_all_raw()
        if raw_data is None:
            self.running = False
            return

        for key in raw_data:
            value = raw_data.get(key)
            raw_data[key] = value
            if not value:
                continue

            if "struct" in value and "dashboard" in value["struct"]:
                structured = {}
                for viewable in value["struct"]["dashboard"]:
                    display = ""
                    if "element" in viewable:
                        raw = value.get(viewable["element"], "")
                        if "format" in viewable:
                            fmt = viewable["format"]
                            if fmt == "percent":
                                display = f"{raw * 100:.2f}%"
                            elif fmt == "degrees":
                                display = f"{raw}°"
                            elif fmt == "radians":
                                display = f"{raw} rad"
                            elif fmt.startswith("limit:"):
                                limit = int(fmt.split(":")[1])
                                display = raw[:limit]
                            else:
                                display = raw

                        structured[viewable["element"]] = display
                data[key] = structured

        def to_hierarchical_dict(flat_dict: dict):
            hierarchical_dict = {}
            for k, v in flat_dict.items():
                parts = k.split("/")
                d = hierarchical_dict
                for part in parts[:-1]:
                    d = d.setdefault(part, {})
                d[parts[-1]] = {"items": v, "key": k}
            return hierarchical_dict

        hierarchical = to_hierarchical_dict(data)

        expanded_indexes = []

        def store_expansion(parent):
            for row in range(self.model.rowCount(parent)):
                index = self.model.index(row, 0, parent)
                if self.tree.isExpanded(index):
                    expanded_indexes.append((self.get_index_path(index), True))
                store_expansion(index)

        store_expansion(QModelIndex())

        selected_paths = [
            self.get_index_path(index) for index in self.tree.selectionModel().selectedIndexes() if index.column() == 0
        ]

        for widget in self.controller.get_items():
            if widget.key in raw_data:
                widget.update_data(raw_data[widget.key])

        self.result_ready.emit(hierarchical, expanded_indexes, selected_paths, raw_data)
        self.running = False


class Application(ThemableWindow):
    on_disconnect_signal = Signal()
    on_connect_signal = Signal()

    def __init__(self, app: QApplication, logger: Logger):
        super().__init__()
        self.app = app
        self.setWindowTitle("KevinbotLib Dashboard")
        self.setWindowIcon(QIcon(":/app_icons/dashboard-small.svg"))

        self.settings = QSettings("kevinbotlib", "dashboard")

        self.logger = logger

        self.theme = Theme(ThemeStyle.System)

        self.graphics_view = GridGraphicsView(
            grid_size=self.settings.value("grid", 48, int),  # type: ignore
            rows=self.settings.value("rows", 10, int),  # type: ignore
            cols=self.settings.value("cols", 10, int),  # type: ignore
            theme=GridThemes.Dark,
        )
        self.apply_theme()

        self.on_connect_signal.connect(self.on_connect)
        self.on_disconnect_signal.connect(self.on_disconnect)

        self.client = RedisCommClient(
            host=self.settings.value("ip", "10.0.0.2", str),  # type: ignore
            port=self.settings.value("port", 6379, int),  # type: ignore
            on_disconnect=self.on_disconnect_signal.emit,
            on_connect=self.on_connect_signal.emit,
        )
        VisionCommUtils.init_comms_types(self.client)

        self.notifier = Notifier(self)

        self.menu = self.menuBar()
        self.menu.setNativeMenuBar(sys.platform != "Darwin")

        self.file_menu = self.menu.addMenu("&File")

        self.save_action = self.file_menu.addAction("Save Layout", self.save_slot)
        self.save_action.setShortcut("Ctrl+S")

        self.quit_action = self.file_menu.addAction("Quit", self.close)
        self.quit_action.setShortcut("Alt+F4")

        self.edit_menu = self.menu.addMenu("&Edit")

        self.settings_action = self.edit_menu.addAction("Settings", self.open_settings)
        self.settings_action.setShortcut("Ctrl+,")

        self.help_menu = self.menu.addMenu("&Help")

        self.about_action = self.help_menu.addAction("About", self.show_about)

        self.status = self.statusBar()

        self.connection_status = QLabel("Robot Disconnected")
        self.status.addWidget(self.connection_status)

        self.ip_status = QLabel(str(self.settings.value("ip", "10.0.0.2", str)), alignment=Qt.AlignmentFlag.AlignCenter)
        self.status.addWidget(self.ip_status, 1)

        self.latency_status = QLabel("Latency: 0.00")
        self.status.addPermanentWidget(self.latency_status)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        root_layout = QVBoxLayout(main_widget)

        main_layout = QHBoxLayout()
        root_layout.addLayout(main_layout, 999)
        self.widget_palette = WidgetPalette(self.graphics_view, self.client)
        self.model = self.widget_palette.model
        self.tree = self.widget_palette.tree

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.graphics_view)
        splitter.addWidget(self.widget_palette)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

        self.log_queue: Queue[str] = Queue(1000)
        self.logger.add_hook_ansi(self.log_hook)
        sys.excepthook = self._exc_hook

        self.log_timer = QTimer()
        self.log_timer.setInterval(250)
        self.log_timer.timeout.connect(self.update_logs)
        self.log_timer.start()

        self.log_widget = QWidget()
        self.log_widget.setContentsMargins(0, 0, 0, 0)
        self.log_widget.hide()
        root_layout.addWidget(self.log_widget)

        log_layout = QVBoxLayout(self.log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0)

        self.log_view = QTextEdit(placeholderText="No logs yet")
        self.log_view.setReadOnly(True)
        self.log_view.setWordWrapMode(QTextOption.WrapMode.NoWrap)
        self.log_view.document().setMaximumBlockCount(100)
        log_layout.addWidget(self.log_view)

        log_collapse = QToolButton()
        log_collapse.setText("Dashboard Logs")
        log_collapse.setStyleSheet("padding: 2px;")
        log_collapse.setFixedHeight(24)
        log_collapse.clicked.connect(self.toggle_logs)
        root_layout.addWidget(log_collapse, alignment=Qt.AlignmentFlag.AlignCenter)

        self.log_open_animation = QPropertyAnimation(self.log_widget, b"maximumHeight")  # type: ignore
        self.log_open_animation.setStartValue(0)
        self.log_open_animation.setEndValue(200)
        self.log_open_animation.setDuration(100)

        self.log_close_animation = QPropertyAnimation(self.log_widget, b"maximumHeight")  # type: ignore
        self.log_close_animation.setStartValue(200)
        self.log_close_animation.setEndValue(0)
        self.log_close_animation.setDuration(100)
        self.log_close_animation.finished.connect(self.log_widget.hide)

        self.latency_thread = QThread(self)
        self.latency_worker = LatencyWorker(self.client)
        self.latency_worker.moveToThread(self.latency_thread)
        self.latency_thread.start()
        self.latency_worker.latency.connect(self.update_latency)

        self.latency_timer = QTimer()
        self.latency_timer.setInterval(1000)
        self.latency_timer.timeout.connect(self.latency_worker.get_latency.emit)
        self.latency_timer.start()

        self.controller = WidgetGridController(self.graphics_view)
        self.controller.load(lambda x: item_loader(self, x), self.settings.value("layout", [], type=list))  # type: ignore

        self.tree_worker_thread = QThread(self)
        self.tree_worker = PollingWorker(
            client=self.client,
            model=self.model,
            tree=self.tree,
            get_index_path=self.get_index_path,
            controller=self.controller,
        )
        self.tree_worker.moveToThread(self.tree_worker_thread)
        self.tree_worker.result_ready.connect(self._apply_tree_update)
        self.tree_worker_thread.start()

        self.update_timer = QTimer()
        self.update_timer.setInterval(self.settings.value("rate", 200, int))  # type: ignore
        self.update_timer.timeout.connect(self.tree_worker.run)
        self.update_timer.start()

        self.settings_window = SettingsWindow(self, self.settings)
        self.settings_window.on_applied.connect(self.refresh_settings)

        self.about_window = AboutDialog(
            "KevinbotLib Dashboard",
            "Robot Dashboard for KevinbotLib",
            __version__,
            "\nSource code is licensed under the GNU LGPLv3\nBinaries are licensed under the GNU GPLv3, due to some GPL components\nSee 'Open Source Licenses' for more details...",
            QIcon(":/app_icons/dashboard.svg"),
            "Copyright © 2025 Kevin Ahr and contributors",
            self,
        )

        self.connection_governor_thread = Thread(
            target=self.connection_governor, daemon=True, name="KevinbotLib.Dashboard.Connection.Governor"
        )
        self.connection_governor_thread.start()

    def show_about(self):
        self.about_window.show()

    def _exc_hook(self, _: type, exc_value: BaseException, __: TracebackType, *_args):
        self.logger.log(
            Level.CRITICAL,
            "Dashboard exception",
            LoggerWriteOpts(exception=exc_value),
        )

    def log_hook(self, data: str):
        self.log_queue.put(ansi2html.Ansi2HTMLConverter(scheme="osx").convert(data.strip()))

    def update_logs(self):
        while not self.log_queue.empty():
            self.log_view.append(self.log_queue.get())

    def toggle_logs(self):
        if not self.log_widget.isVisible():
            self.log_widget.show()
            self.log_open_animation.start()
        else:
            # noinspection PyAttributeOutsideInit
            self.log_close_animation.start()

    def connection_governor(self):
        while True:
            if not self.client.is_connected():
                self.client.connect()
            time.sleep(2)

    def apply_theme(self):
        theme_name = self.settings.value("theme", "Dark")
        if theme_name == "Dark":
            qta.dark(self.app)
            self.theme.set_style(ThemeStyle.Dark)
            self.graphics_view.set_theme(GridThemes.Dark)
        elif theme_name == "Light":
            qta.light(self.app)
            self.theme.set_style(ThemeStyle.Light)
            self.graphics_view.set_theme(GridThemes.Light)
        else:
            self.theme.set_style(ThemeStyle.System)
            if self.theme.is_dark():
                qta.dark(self.app)
                self.graphics_view.set_theme(GridThemes.Dark)
            else:
                qta.light(self.app)
                self.graphics_view.set_theme(GridThemes.Light)
        self.theme.apply(self)

    def update_latency(self, latency: float | None):
        if latency:
            self.latency_status.setText(f"Latency: {latency:.2f}ms")
        else:
            self.latency_status.setText("Latency: --.--ms")

    @Slot(dict, list, list, dict)
    def _apply_tree_update(self, hierarchical_data, expanded_indexes, selected_paths, raw_data):
        self.model.update_data(hierarchical_data)
        self.widget_palette.panel.raw_data = raw_data

        for path, was_expanded in expanded_indexes:
            index = self.get_index_from_path(path)
            if index.isValid() and was_expanded:
                self.tree.setExpanded(index, True)

        selection_model = self.tree.selectionModel()
        selection_model.clear()
        for path in selected_paths:
            index = self.get_index_from_path(path)
            if index.isValid():
                selection_model.select(index, selection_model.SelectionFlag.Select | selection_model.SelectionFlag.Rows)

    def update_tree(self):
        self.tree_worker.run()

    def get_selection_paths(self):
        return [
            self.get_index_path(index) for index in self.tree.selectionModel().selectedIndexes() if index.column() == 0
        ]

    def restore_selection(self, paths):
        selection_model = self.tree.selectionModel()
        selection_model.clear()
        for path in paths:
            index = self.get_index_from_path(path)
            if index.isValid():
                selection_model.select(index, selection_model.SelectionFlag.Select | selection_model.SelectionFlag.Rows)

    def get_index_path(self, index):
        path = []
        while index.isValid():
            path.append(index.row())
            index = self.model.parent(index)
        return tuple(reversed(path))

    def get_index_from_path(self, path):
        index = QModelIndex()
        for row in path:
            index = self.model.index(row, 0, index)
        return index

    def on_connect(self):
        self.connection_status.setText("Robot Connected")
        self.update_tree()

    def on_disconnect(self):
        self.connection_status.setText("Robot Disconnected")

    def refresh_settings(self):
        self.settings.setValue("ip", self.settings_window.net_ip.text())
        self.settings.setValue("port", self.settings_window.net_port.value())
        if self.client.host != self.settings.value("ip", "10.0.0.2", str):  # type: ignore
            self.client.host = self.settings.value("ip", "10.0.0.2", str)  # type: ignore
        if self.client.port != self.settings.value("port", 6379, int):  # type: ignore
            self.client.port = self.settings.value("port", 6379, int)  # type: ignore

        self.ip_status.setText(str(self.settings.value("ip", "10.0.0.2", str)))

        self.settings.setValue("grid", self.settings_window.grid_size.value())
        self.settings.setValue("rows", self.settings_window.grid_rows.value())
        self.settings.setValue("cols", self.settings_window.grid_cols.value())

        self.graphics_view.set_grid_size(self.settings.value("grid", 48, int))  # type: ignore
        if not self.graphics_view.resize_grid(
            self.settings.value("rows", 10, int),  # type: ignore
            self.settings.value("cols", 10, int),  # type: ignore
        ):
            QMessageBox.critical(self.settings_window, "Error", "Cannot resize grid to the specified dimensions.")
            self.settings.setValue("rows", self.graphics_view.rows)
            self.settings.setValue("cols", self.graphics_view.cols)

        self.settings.setValue("rate", self.settings_window.poll_rate.value())
        self.update_timer.setInterval(self.settings.value("rate", 200, int))  # type: ignore

    @override
    def closeEvent(self, event: QCloseEvent):
        if self.controller.get_widgets() == self.settings.value("layout", [], type=list):  # type: ignore
            event.accept()
            return

        reply = QMessageBox.question(
            self,
            "Save Layout",
            "Do you want to save the current layout before exiting?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.save_slot()
            self.tree_worker_thread.quit()
            self.latency_thread.quit()
            for widget in self.controller.get_items():
                widget.close()
            event.accept()
        elif reply == QMessageBox.StandardButton.No:
            self.tree_worker_thread.quit()
            self.latency_thread.quit()
            for widget in self.controller.get_items():
                widget.close()
            event.accept()
        else:
            event.ignore()

    def save_slot(self):
        self.settings.setValue("layout", self.controller.get_widgets())
        self.notifier.toast("Layout Saved", "Layout saved successfully", severity=Severity.Success)

    def open_settings(self):
        self.settings_window.show()


@dataclass
class DashboardApplicationStartupArguments:
    verbose: bool = False
    trace: bool = True


class DashboardApplicationRunner:
    def __init__(self, args: DashboardApplicationStartupArguments | None = None):
        self.logger = Logger()
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("KevinbotLib Dashboard")
        self.app.setApplicationVersion(__version__)
        self.app.setStyle("Fusion")  # can solve some platform-specific issues

        self.configure_logger(args)
        self.window = None

    def configure_logger(self, args: DashboardApplicationStartupArguments | None):
        # this is needed on Windows when using --windowed in PyInstaller
        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w")  # noqa: SIM115
        if sys.stderr is None:
            sys.stderr = open(os.devnull, "w")  # noqa: SIM115

        if args is None:
            parser = QCommandLineParser()
            parser.addHelpOption()
            parser.addVersionOption()
            parser.addOption(QCommandLineOption(["V", "verbose"], "Enable verbose (DEBUG) logging"))
            parser.addOption(
                QCommandLineOption(
                    ["T", "trace"],
                    QCoreApplication.translate("main", "Enable tracing (TRACE logging)"),
                )
            )
            parser.process(self.app)

            log_level = Level.INFO
            if parser.isSet("verbose"):
                log_level = Level.DEBUG
            elif parser.isSet("trace"):
                log_level = Level.TRACE
        else:
            log_level = Level.INFO
            if args.verbose:
                log_level = Level.DEBUG
            elif args.trace:
                log_level = Level.TRACE

        self.logger.configure(LoggerConfiguration(level=log_level))

    def run(self):
        kevinbotlib.apps.dashboard.resources_rc.qInitResources()
        self.window = Application(self.app, self.logger)
        self.window.show()
        sys.exit(self.app.exec())


def execute(args: DashboardApplicationStartupArguments | None):
    runner = DashboardApplicationRunner(args)
    runner.run()


if __name__ == "__main__":
    execute(None)
