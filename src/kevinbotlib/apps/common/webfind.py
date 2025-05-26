from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout


class FindDialog(QDialog):
    def __init__(self, web_view: QWebEngineView, parent=None):
        super().__init__(parent)
        self.web_view = web_view
        self.setWindowTitle("Find")
        self.setFixedWidth(300)

        # Layout
        layout = QVBoxLayout()

        # Find input
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Enter search text...")
        layout.addWidget(QLabel("Find:"))
        layout.addWidget(self.find_input)

        # Case sensitivity checkbox
        self.case_sensitive = QCheckBox("Match Case")
        layout.addWidget(self.case_sensitive)

        # Buttons
        button_layout = QHBoxLayout()
        self.find_next = QPushButton("Find Next")
        self.find_prev = QPushButton("Find Previous")
        button_layout.addWidget(self.find_next)
        button_layout.addWidget(self.find_prev)
        layout.addLayout(button_layout)

        # Connect signals
        self.find_input.textChanged.connect(self.find_text)
        self.find_next.clicked.connect(self.find_next_text)
        self.find_prev.clicked.connect(self.find_prev_text)
        self.case_sensitive.stateChanged.connect(self.find_text)

        self.setLayout(layout)

    def find_text(self):
        text = self.find_input.text()
        if text:
            flags = (
                QWebEnginePage.FindFlag.FindCaseSensitively
                if self.case_sensitive.isChecked()
                else QWebEnginePage.FindFlag(0)
            )
            self.web_view.findText(text, flags)

    def find_next_text(self):
        flags = (
            QWebEnginePage.FindFlag.FindCaseSensitively
            if self.case_sensitive.isChecked()
            else QWebEnginePage.FindFlag(0)
        )
        self.web_view.findText(self.find_input.text(), flags)

    def find_prev_text(self):
        flags = QWebEnginePage.FindFlag.FindBackward
        if self.case_sensitive.isChecked():
            flags |= QWebEnginePage.FindFlag.FindCaseSensitively
        self.web_view.findText(self.find_input.text(), flags)

    def closeEvent(self, _event):  # noqa: N802
        self.web_view.findText("")
