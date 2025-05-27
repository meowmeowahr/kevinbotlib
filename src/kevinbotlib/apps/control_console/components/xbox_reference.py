from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QVBoxLayout

from kevinbotlib.joystick import XboxControllerAxis, XboxControllerButtons


class XboxDefaultButtonMapWidget(QGroupBox):
    def __init__(self):
        super().__init__("Xbox Button Reference")

        self.root_layout = QGridLayout()
        self.setLayout(self.root_layout)

        for i, value in enumerate(XboxControllerButtons):
            name = XboxControllerButtons(value).name
            uppercase_letters = "".join(c for c in name if c.isupper())
            display_name = uppercase_letters if len(uppercase_letters) >= 2 else name  # noqa: PLR2004
            label = QLabel(f"{display_name} -> <b>{value}</b>")
            self.root_layout.addWidget(label, i // 2, i % 2)


class XboxDefaultAxisMapWidget(QGroupBox):
    def __init__(self):
        super().__init__("Xbox Axis Reference")

        self.root_layout = QVBoxLayout()
        self.setLayout(self.root_layout)

        for value in XboxControllerAxis:
            label = QLabel(f"{XboxControllerAxis(value).name.title()} -> <b>{value}</b>")
            self.root_layout.addWidget(label)
