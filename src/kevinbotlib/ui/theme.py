import pathlib
from enum import Enum

import darkdetect
import jinja2
from PySide6.QtWidgets import QApplication, QMainWindow


class ThemeStyle(Enum):
    Light = 0
    Dark = 1
    System = 2


class Theme:
    def __init__(self, style: ThemeStyle):
        self.style = style
        self.app: QApplication | QMainWindow | None = None

    def get_stylesheet(self):
        try:
            template_loader = jinja2.FileSystemLoader(searchpath=pathlib.Path(__file__).parent.resolve())
            template_env = jinja2.Environment(loader=template_loader, autoescape=True)
            template = template_env.get_template("base.qss")

            context = {
                "is_dark": self.style == ThemeStyle.Dark or (self.style == ThemeStyle.System and darkdetect.isDark())
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
