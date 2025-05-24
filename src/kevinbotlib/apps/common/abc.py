from abc import abstractmethod

from PySide6.QtWidgets import QMainWindow


class ThemableWindow(QMainWindow):
    @abstractmethod
    def apply_theme(self):
        pass
