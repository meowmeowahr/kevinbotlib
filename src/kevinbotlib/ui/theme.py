import pathlib
from enum import Enum

import darkdetect
import jinja2
from PySide6.QtWidgets import QApplication, QMainWindow

import kevinbotlib.ui.resources_rc

kevinbotlib.ui.resources_rc.qInitResources()


class ThemeStyle(Enum):
    Light = 0
    Dark = 1
    System = 2


class Theme:
    def __init__(self, style: ThemeStyle):
        self.style = style
        self.app: QApplication | QMainWindow | None = None

    def is_dark(self):
        if self.style == ThemeStyle.Dark:
            return True
        if self.style == ThemeStyle.Light:
            return False
        return darkdetect.isDark()

    def get_stylesheet(self):
        try:
            template_loader = jinja2.FileSystemLoader(searchpath=pathlib.Path(__file__).parent.resolve())
            template_env = jinja2.Environment(loader=template_loader, autoescape=True)
            template = template_env.get_template("base.qss")

            context = {
                "is_dark": self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark()),
                "bg1": "#1a2326"
                if self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark())
                else "#eeeeee",
                "bg2": "#1e272a"
                if self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark())
                else "#ffffff",
                "bg3": "#252d31"
                if self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark())
                else "#e6e6e6",
                "bg4": "#30383b"
                if self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark())
                else "#dcdcdc",
                "bg5": "#40484c"
                if self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark())
                else "#c5c5c5",
                "border": "#2d3639"
                if self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark())
                else "#d5d5d5",
                "fg": "#d0d8d8"
                if self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark())
                else "#333333",
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

    def apply(self, app: QApplication | QMainWindow):
        app.setStyleSheet(self.get_stylesheet())
        self.app = app

    def set_style(self, style: ThemeStyle):
        self.style = style
        if self.app:
            self.app.setStyleSheet(self.get_stylesheet())
