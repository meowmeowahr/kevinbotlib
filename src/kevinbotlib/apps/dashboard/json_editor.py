import json
import re

from PySide6.QtCore import QObject
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import QTextEdit


class JsonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent if parent else QObject())

        self.highlighting_rules = []

        # Define formats
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))
        keyword_format.setFontWeight(QFont.Weight.Bold)

        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#EE9178"))

        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5DEA8"))

        punctuation_format = QTextCharFormat()
        punctuation_format.setForeground(QColor("#D4D4D4"))

        null_format = QTextCharFormat()
        null_format.setForeground(QColor("#569CD6"))
        null_format.setFontWeight(QFont.Weight.Bold)

        # Define patterns
        self.highlighting_rules.append((r"\btrue\b|\bfalse\b", keyword_format))
        self.highlighting_rules.append((r"\bnull\b", null_format))
        self.highlighting_rules.append((r'"[^"\\]*(?:\\.[^"\\]*)*"', string_format))
        self.highlighting_rules.append((r"-?\d*\.?\d+(?:[eE][-+]?\d+)?", number_format))
        self.highlighting_rules.append((r"[\{\}\[\],:]", punctuation_format))

    def highlightBlock(self, text):  # noqa: N802
        # Apply each highlighting rule
        for pattern, fmt in self.highlighting_rules:
            for match in re.finditer(pattern, text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)

        # Set the current block state
        self.setCurrentBlockState(0)


class JsonEditor(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setFont(QFont("monospace", 10))
        self.highlighter = JsonHighlighter(self.document())
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E20;
                color: #D4D4D4;
                border: 1px solid #404040;
            }
        """)

        self.textChanged.connect(self.validate_json)

    def validate_json(self):
        """Validate JSON and set background color based on validity"""
        text = self.toPlainText()
        try:
            json.loads(text)
            self.setStyleSheet("""
                QTextEdit {
                    background-color: #1E1E20;
                    color: #D4D4D4;
                    border: 1px solid #404040;
                }
            """)
        except json.JSONDecodeError:
            self.setStyleSheet("""
                QTextEdit {
                    background-color: #2E1E20;
                    color: #D4D4D4;
                    border: 1px solid #FF4040;
                }
            """)
