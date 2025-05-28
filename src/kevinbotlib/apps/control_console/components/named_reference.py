from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QVBoxLayout

from kevinbotlib.joystick import NamedControllerAxis, NamedControllerButtons


class NamedDefaultButtonMapWidget(QGroupBox):
    def __init__(self):
        super().__init__("Named Button Reference")

        self.root_layout = QGridLayout()
        self.setLayout(self.root_layout)

        for i, value in enumerate(NamedControllerButtons):
            name = NamedControllerButtons(value).name
            uppercase_letters = "".join(c for c in name if c.isupper())
            display_name = uppercase_letters if len(uppercase_letters) >= 2 else name  # noqa: PLR2004
            label = QLabel(f"{display_name} -> <b>{value}</b>")
            self.root_layout.addWidget(label, i // 3, i % 3)


class NamedDefaultAxisMapWidget(QGroupBox):
    def __init__(self):
        super().__init__("Named Axis Reference")

        self.root_layout = QVBoxLayout()
        self.setLayout(self.root_layout)

        for value in NamedControllerAxis:
            label = QLabel(f"{NamedControllerAxis(value).name.title()} -> <b>{value}</b>")
            self.root_layout.addWidget(label)
