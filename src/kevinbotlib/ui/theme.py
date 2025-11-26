import pathlib
import sys
from enum import Enum

import darkdetect
import jinja2
from qtpy.QtWidgets import QApplication, QMainWindow

import kevinbotlib_theme

class ThemeStyle(Enum):
    """Theme options for the KevinbotLib UI theme"""

    Light = 0
    """Light mode"""
    Dark = 1
    """Dark mode"""
    System = 2
    """System theme, uses GTK on Linux, and system preference on Windows/macOS"""


class Theme:
    """Qt theming engine for the KevinbotLib UI style"""

    def __init__(self, style: ThemeStyle):
        """
        Initialize the theming system.

        Args:
            style: Theme to use.
        """
        self.style = style
        self.app: QApplication | QMainWindow | None = None

    def is_dark(self) -> bool:
        """
        Detect if the currently applied style is dark

        Returns:
            bool: Is the current style dark?
        """
        if self.style == ThemeStyle.Dark:
            return True
        if self.style == ThemeStyle.Light:
            return False
        return darkdetect.isDark()

    def apply(self, app: QApplication | QMainWindow) -> None:
        """
        Apply the theme to an application or window

        Args:
            app: App or window to apply the theme to.
        """

        match self.style:
            case ThemeStyle.System:
                app.setStyleSheet(kevinbotlib_theme.load_stylesheet("auto"))
            case ThemeStyle.Light:
                app.setStyleSheet(kevinbotlib_theme.load_stylesheet("light"))
            case ThemeStyle.Dark:
                app.setStyleSheet(kevinbotlib_theme.load_stylesheet("dark"))

        self.app = app

    def set_style(self, style: ThemeStyle) -> None:
        """
        Apply a new theme to the application or window.

        Args:
            style: ThemeStyle. Theme to use.
        """
        self.style = style
        if self.app:
            self.apply(self.app)
