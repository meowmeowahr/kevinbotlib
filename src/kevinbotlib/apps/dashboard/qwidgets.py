from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QWidget


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
