import pathlib
import sys
from enum import Enum

import darkdetect
import jinja2
from qtpy.QtWidgets import QApplication, QMainWindow

import kevinbotlib.ui.resources_rc

kevinbotlib.ui.resources_rc.qInitResources()  # this shouldn't be required, make linters happy


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

    def get_stylesheet(self) -> str:
        """
        Get the formatted stylesheet string to apply

        Returns:
            str: Qt QSS Stylesheet string.
        """
        try:
            # this is needed for PyInstaller - base.qss gets moved to sys._MEIPASS
            if getattr(sys, "frozen", False):  # Running in a bundle
                # noinspection PyProtectedMember
                base_path = pathlib.Path(sys._MEIPASS)  # noqa: SLF001
            else:  # Running from source
                base_path = pathlib.Path(__file__).parent.resolve()
            template_loader = jinja2.FileSystemLoader(searchpath=base_path)
            template_env = jinja2.Environment(loader=template_loader, autoescape=True)
            template = template_env.get_template("base.qss")

            context = {
                "is_dark": self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark()),
                "bg1": "#0a1316"
                if self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark())
                else "#eeeeee",
                "bg2": "#0e171a"
                if self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark())
                else "#ffffff",
                "bg3": "#151d21"
                if self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark())
                else "#e6e6e6",
                "bg4": "#20282b"
                if self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark())
                else "#dcdcdc",
                "bg5": "#30383c"
                if self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark())
                else "#c5c5c5",
                "border": "#2d3639"
                if self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark())
                else "#d5d5d5",
                "fg": "#d0d8d8"
                if self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark())
                else "#333333",
                "fg_disabled": "#606868"
                if self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark())
                else "#636363",
                "fg_highlight": "#ffffff"
                if self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark())
                else "#1a1a1a",
                "primary1": "#4682b4"
                if self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark())
                else "#4169e1",
                "primary2": "#5a9bd4"
                if self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark())
                else "#5a8cff",
                "selection": "#4682b4"
                if self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark())
                else "#cce7ff",
            }

            return template.render(context)
        except jinja2.TemplateNotFound:
            return ""

    def apply(self, app: QApplication | QMainWindow) -> None:
        """
        Apply the theme to an application or window

        Args:
            app: App or window to apply the theme to.
        """
        app.setStyleSheet(self.get_stylesheet())
        self.app = app

    def set_style(self, style: ThemeStyle) -> None:
        """
        Apply a new theme to the application or window.

        Args:
            style: ThemeStyle. Theme to use.
        """
        self.style = style
        if self.app:
            self.app.setStyleSheet(self.get_stylesheet())
