from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSizePolicy,
    QWidget,
)

from kevinbotlib.apps.common.abc import ThemableWindow


class UiColorSettingsSwitcher(QFrame):
    def __init__(
        self,
        settings: QSettings,
        key: str,
        main_window: ThemableWindow,
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


class Divider(QWidget):
    def __init__(self, text: str):
        super().__init__()

        _layout = QHBoxLayout()
        self.setLayout(_layout)

        self.label = QLabel(text)
        _layout.addWidget(self.label)

        self.line = QFrame()
        self.line.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.line.setFrameShape(QFrame.Shape.HLine)
        _layout.addWidget(self.line)
