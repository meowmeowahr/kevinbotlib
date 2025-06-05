import multiprocessing
import sys

from PySide6.QtCore import QByteArray, QSettings, Qt, QTimer, Signal, QUrl
from PySide6.QtGui import QAction, QFont, QIcon, QPixmap, QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMdiArea,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import kevinbotlib.simulator.resources_rc as _rcc
from kevinbotlib import __about__
from kevinbotlib.apps.common.abc import ThemableWindow as _ThemableWindow
from kevinbotlib.apps.common.about import AboutDialog
from kevinbotlib.apps.common.settings_rows import Divider, UiColorSettingsSwitcher
from kevinbotlib.apps.common.toast import NotificationWidget, Severity
from kevinbotlib.logger import Logger, LoggerDirectories
from kevinbotlib.simulator._events import (
    _AddWindowEvent,
    _ExitSimulatorEvent,
    _SimulatorExitEvent,
    _WindowViewPayloadEvent,
    _WindowViewUpdateEvent,
)
from kevinbotlib.simulator._mdi import _MdiChild
from kevinbotlib.simulator.windowview import WINDOW_VIEW_REGISTRY, WindowView
from kevinbotlib.ui.theme import Theme, ThemeStyle


class SettingsWindow(QDialog):
    on_applied = Signal()

    def __init__(self, parent: "SimMainWindow", settings: QSettings):
        super().__init__(parent=parent)
        self.setModal(True)
        self.setWindowTitle("Settings")

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


class SimMainWindow(_ThemableWindow):
    def __init__(self, in_queue: multiprocessing.Queue, out_queue: multiprocessing.Queue):
        super().__init__()
        self._in_queue = in_queue
        self._queue_drain_timer = QTimer(self)
        self._queue_drain_timer.timeout.connect(self._drain_queue)
        self._queue_drain_timer.start(0)  # run every event-loop iteration

        self.out_queue = out_queue

        _rcc.qInitResources()
        self.setWindowTitle("Simulator")
        self.setWindowIcon(QIcon(":/app_icons/simulator.svg"))

        self.settings = QSettings("kevinbotlib", "simframework")
        self.theme = Theme(ThemeStyle.System)

        self.settings_window = SettingsWindow(self, self.settings)
        self.about_window = AboutDialog(
            "KevinbotLib Simulation Framework",
            "Simulate Robot Hardware",
            __about__.__version__,
            "\nSource code is licensed under the GNU LGPLv3\n"
            "Binaries are licensed under the GNU GPLv3 due to some GPL components\n"
            "See 'Open Source Licenses' for more details...",
            QIcon(":/app_icons/simulator.svg"),
            "Copyright © 2025 Kevin Ahr and contributors",
            self,
        )

        self.menu = self.menuBar()
        self.menu.setNativeMenuBar(sys.platform != "Darwin")

        self.file_menu: QMenu = self.menu.addMenu("&File")

        self.open_logs_action = self.file_menu.addAction("Open Log Location", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(LoggerDirectories.get_logger_directory(ensure_exists=True))))

        self.quit_action = self.file_menu.addAction("Quit", self.close)
        self.quit_action.setShortcut("Alt+F4")

        self.edit_menu: QMenu = self.menu.addMenu("&Edit")
        self.settings_action = self.edit_menu.addAction("Settings", self.open_settings)
        self.settings_action.setShortcut("Ctrl+,")

        self.windows_menu: QMenu = self.menu.addMenu("&Windows")

        self.help_menu: QMenu = self.menu.addMenu("&Help")
        self.about_action = self.help_menu.addAction("About", self.show_about)

        self.widget = QWidget()
        self.setCentralWidget(self.widget)

        self.root_layout = QVBoxLayout(self.widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)

        self.top_bar = QHBoxLayout()
        self.top_bar.setContentsMargins(8, 8, 8, 0)
        self.root_layout.addLayout(self.top_bar)

        self.top_bar_icon = QLabel()
        self.top_bar_icon.setPixmap(QIcon(":/app_icons/console.svg").pixmap(48, 48))
        self.top_bar.addWidget(self.top_bar_icon)

        self.top_bar_text_stack = QVBoxLayout()
        self.top_bar.addLayout(self.top_bar_text_stack)
        self.top_bar_text_stack.addStretch()

        self.top_bar_title = QLabel("KevinbotLib Simulation Framework")
        self.top_bar_title.setFont(QFont(self.font().family(), 13))
        self.top_bar_text_stack.addWidget(self.top_bar_title)

        self.top_bar.addStretch()

        self.top_bar_version = QLabel(__about__.__version__)
        self.top_bar_version.setFont(QFont(self.font().family(), 10))
        self.top_bar_text_stack.addWidget(self.top_bar_version)
        self.top_bar_text_stack.addStretch()

        self.divider = QFrame()
        self.divider.setContentsMargins(8, 8, 8, 8)
        self.divider.setFrameShape(QFrame.Shape.HLine)
        self.root_layout.addWidget(self.divider)

        self.mdi = QMdiArea()
        self.mdi.setOption(QMdiArea.AreaOption.DontMaximizeSubWindowOnActivation)
        self.mdi.setBackground(
            QPixmap(":/mdi_background/grid-dark.svg" if self.theme.is_dark() else ":/mdi_background/grid-light.svg")
        )
        self.root_layout.addWidget(self.mdi, 9999)

        self._mdi_children: dict[str, _MdiChild] = {}
        self.views: dict[str, WindowView] = {}

        self.apply_theme()

    def _drain_queue(self):
        """Handle everything currently waiting in `in_queue`."""
        while not self._in_queue.empty():
            event = self._in_queue.get_nowait()

            if isinstance(event, _WindowViewUpdateEvent):
                view = self.views.get(event.view_name)
                if view is not None:  # wrong name ⇒ silently ignore
                    view.update(event.payload)
            elif isinstance(event, _AddWindowEvent):
                self._handle_add_window_event(event)
            elif isinstance(event, _ExitSimulatorEvent):
                self.close()

    def _handle_add_window_event(self, event: "_AddWindowEvent"):
        cls = WINDOW_VIEW_REGISTRY.get(event.name)
        if cls is None:
            Logger().warning(f"No registered window view for {event.name}")
            return
        instance = cls()
        self.add_window(event.name, instance, default_open=event.default_open)

    def add_window(
        self,
        winid: str,
        view: WindowView,
        *,
        default_open: bool = False,
    ) -> QWidget:
        view.send_payload = lambda x: self.out_queue.put_nowait(_WindowViewPayloadEvent(winid, x))

        self.views[winid] = view
        action: QAction = self.windows_menu.addAction(view.title)

        def _show_window() -> QWidget:
            mdi_child = self._mdi_children.get(winid)
            if mdi_child and mdi_child.isVisible():
                mdi_child.setFocus(Qt.FocusReason.OtherFocusReason)
                self.mdi.setActiveSubWindow(mdi_child)
                return view.generate()

            inner = view.generate()
            mdi_child = _MdiChild(winid, view.title, inner, self.settings)
            self._mdi_children[winid] = mdi_child
            self.mdi.addSubWindow(mdi_child)

            mdi_child.show()

            geo: QByteArray = self.settings.value(f"windows/{winid}/geometry", None)  # type: ignore
            if geo is not None:
                mdi_child.restoreGeometry(geo)

            self.mdi.setActiveSubWindow(mdi_child)

            return inner

        action.triggered.connect(_show_window)

        visible_key = f"windows/{winid}/visible"
        was_visible = self.settings.value(visible_key, type=bool, defaultValue=default_open)
        if was_visible:
            return _show_window()
        return QWidget()

    def apply_theme(self) -> None:
        theme_name = self.settings.value("theme", "Dark")
        if theme_name == "Dark":
            self.theme.set_style(ThemeStyle.Dark)
        elif theme_name == "Light":
            self.theme.set_style(ThemeStyle.Light)
        else:
            self.theme.set_style(ThemeStyle.System)
        self.theme.apply(self)
        self.mdi.setBackground(
            QPixmap(":/mdi_background/grid-dark.svg" if self.theme.is_dark() else ":/mdi_background/grid-light.svg")
        )

    def open_settings(self) -> None:
        self.settings_window.show()

    def show_about(self) -> None:
        self.about_window.show()

    def closeEvent(self, event, /):  # noqa: N802
        for name, child in list(self._mdi_children.items()):
            self.settings.setValue(f"windows/{name}/visible", child.isVisible())
            self.settings.setValue(f"windows/{name}/geometry", child.saveGeometry())

        self.out_queue.put_nowait(_SimulatorExitEvent())
        super().closeEvent(event)
        event.accept()
