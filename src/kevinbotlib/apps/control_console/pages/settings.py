from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QRadioButton,
    QSizePolicy,
    QSpinBox,
    QWidget,
)

if TYPE_CHECKING:
    from kevinbotlib.apps.control_console.control_console import (
        ControlConsoleApplicationWindow,
    )


class ControlConsoleSettingsTab(QWidget):
    settings_changed = Signal()

    def __init__(self, settings: QSettings, main_window: "ControlConsoleApplicationWindow"):
        super().__init__()
        self.settings = settings
        self.main_window = main_window

        self.form = QFormLayout()
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.setLayout(self.form)

        # Theme Setting
        self.form.addRow(
            "Theme",
            UiColorSettingsSwitcher(self.settings, "application.theme", self.main_window),
        )

        # IP Address Setting
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Enter IP address")
        self.ip_input.setText(str(self.settings.value("network.ip", "10.0.0.2")))
        self.ip_input.textChanged.connect(self.save_ip_address)
        self.form.addRow("IP Address", self.ip_input)

        # Port Setting
        self.port_input = QSpinBox()
        self.port_input.setRange(0, 65535)  # Valid port range
        self.port_input.setValue(int(self.settings.value("network.port", 8765)))  # type: ignore
        self.port_input.valueChanged.connect(self.save_port)
        self.form.addRow("Port", self.port_input)

    def save_ip_address(self):
        self.settings.setValue("network.ip", self.ip_input.text())
        self.settings.sync()
        self.settings_changed.emit()

    def save_port(self):
        self.settings.setValue("network.port", self.port_input.value())
        self.settings.sync()
        self.settings_changed.emit()


class UiColorSettingsSwitcher(QFrame):
    def __init__(
        self,
        settings: QSettings,
        key: str,
        main_window: "ControlConsoleApplicationWindow",
    ):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)

        self.settings = settings
        self.key = key
        self.main_window = main_window

        root_layout = QHBoxLayout()
        self.setLayout(root_layout)

        self.dark_mode = QRadioButton("Dark")
        self.light_mode = QRadioButton("Light")
        self.system_mode = QRadioButton("System")

        root_layout.addWidget(self.dark_mode)
        root_layout.addWidget(self.light_mode)
        root_layout.addWidget(self.system_mode)

        # Load saved theme setting
        current_theme = self.settings.value(self.key, "Dark")
        if current_theme == "Dark":
            self.dark_mode.setChecked(True)
        elif current_theme == "Light":
            self.light_mode.setChecked(True)
        else:
            self.system_mode.setChecked(True)

        self.dark_mode.toggled.connect(lambda: self.save_setting("Dark"))
        self.light_mode.toggled.connect(lambda: self.save_setting("Light"))
        self.system_mode.toggled.connect(lambda: self.save_setting("System"))

    def save_setting(self, value: str):
        self.settings.setValue(self.key, value)
        self.settings.sync()
        self.main_window.apply_theme()
