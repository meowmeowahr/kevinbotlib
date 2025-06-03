import base64
import importlib
import math
import os.path
import sys
import time
import typing

import qtawesome
from loguru import logger
from PySide6.QtGui import QImage, QPainter, Qt
from PySide6.QtWidgets import QApplication

from kevinbotlib.apps.dashboard.grid import GridGraphicsView, WidgetGridController
from kevinbotlib.apps.dashboard.grid_theme import Themes
from kevinbotlib.ui.theme import Theme, ThemeStyle

if typing.TYPE_CHECKING:
    from kevinbotlib.apps.dashboard.widgets.base import WidgetItem

CONFIG: typing.Final = {
    "dpi": 120,
    "grid_size": 256,
    "items": [
        {
            "out": "docs/media/dashboard/base-{0}.png",
            "mod": "kevinbotlib.apps.dashboard.widgets.base",
            "class": "WidgetItem",
            "title": "Base Widget",
            "span": [1, 1],
        },
        {
            "out": "docs/media/dashboard/battery-{0}.png",
            "mod": "kevinbotlib.apps.dashboard.widgets.battery",
            "class": "BatteryWidgetItem",
            "title": "Battery Level",
            "span": [1, 1],
            "data": [
                {
                    "value": x,
                    "struct": {"dashboard": [{"element": "value", "format": "raw"}]},
                }
                for x in [round(12 + (math.sin(x / 2) / 4) - x / 10, 2) for x in range(40)]
            ],
        },
        {
            "out": "docs/media/dashboard/graph-{0}.png",
            "mod": "kevinbotlib.apps.dashboard.widgets.graph",
            "class": "GraphWidgetItem",
            "title": "Graph",
            "span": [3, 2],
            "data": [
                {
                    "value": x,
                    "struct": {"dashboard": [{"element": "value", "format": "raw"}]},
                }
                for x in [round(12 + (math.sin(x / 2) / 4) - x / 10, 2) for x in range(40)]
            ],
            "perdata_wait": 0.05,
        },
        {
            "out": "docs/media/dashboard/textedit-{0}.png",
            "mod": "kevinbotlib.apps.dashboard.widgets.textedit",
            "class": "TextEditWidgetItem",
            "title": "Battery Level",
            "span": [1, 1],
        },
        {
            "out": "docs/media/dashboard/text-{0}.png",
            "mod": "kevinbotlib.apps.dashboard.widgets.label",
            "class": "LabelWidgetItem",
            "title": "Text",
            "span": [1, 1],
            "data": [
                {
                    "value": "Demo",
                    "struct": {"dashboard": [{"element": "value", "format": "raw"}]},
                }
            ],
        },
        {
            "out": "docs/media/dashboard/bigtext-{0}.png",
            "mod": "kevinbotlib.apps.dashboard.widgets.biglabel",
            "class": "BigLabelWidgetItem",
            "title": "Big Text",
            "span": [1, 1],
            "data": [
                {
                    "value": "Demo",
                    "struct": {"dashboard": [{"element": "value", "format": "raw"}]},
                }
            ],
        },
        {
            "out": "docs/media/dashboard/boolean-off-{0}.png",
            "mod": "kevinbotlib.apps.dashboard.widgets.boolean",
            "class": "BooleanWidgetItem",
            "title": "Boolean Off",
            "span": [1, 1],
            "data": [
                {
                    "value": False,
                    "struct": {"dashboard": [{"element": "value", "format": "raw"}]},
                }
            ],
        },
        {
            "out": "docs/media/dashboard/boolean-on-{0}.png",
            "mod": "kevinbotlib.apps.dashboard.widgets.boolean",
            "class": "BooleanWidgetItem",
            "title": "Boolean on",
            "span": [1, 1],
            "data": [
                {
                    "value": True,
                    "struct": {"dashboard": [{"element": "value", "format": "raw"}]},
                }
            ],
        },
        {
            "out": "docs/media/dashboard/color-{0}.png",
            "mod": "kevinbotlib.apps.dashboard.widgets.color",
            "class": "ColorWidgetItem",
            "title": "Color",
            "span": [1, 1],
            "data": [
                {
                    "value": "#0000ff",
                    "struct": {"dashboard": [{"element": "value", "format": "raw"}]},
                }
            ],
        },
        {
            "out": "docs/media/dashboard/speedometer-{0}.png",
            "mod": "kevinbotlib.apps.dashboard.widgets.speedometer",
            "class": "SpeedometerWidgetItem",
            "title": "Speedometer",
            "span": [2, 2],
            "data": [
                {
                    "value": 10,
                    "struct": {"dashboard": [{"element": "value", "format": "raw"}]},
                }
            ],
        },
        {
            "out": "docs/media/dashboard/mjpeg-{0}.png",
            "mod": "kevinbotlib.apps.dashboard.widgets.mjpeg",
            "class": "MjpegCameraStreamWidgetItem",
            "title": "MJPEG Stream",
            "span": [3, 2],
            "data": [
                {
                    "value": base64.b64encode(
                        open(  # noqa: SIM115
                            os.path.join(
                                os.path.dirname(os.path.realpath(__file__)),
                                "dashboard.jpg",
                            ),
                            "rb",
                            closefd=True,
                        ).read()
                    ),
                    "struct": {"dashboard": [{"element": "value", "format": "raw"}]},
                }
            ],
            "wait": 2,
        },
        {
            "out": "docs/media/dashboard/slider-{0}.png",
            "mod": "kevinbotlib.apps.dashboard.widgets.slider",
            "class": "SliderWidgetItem",
            "title": "Slider",
            "span": [2, 1],
            "data": [
                {
                    "value": 40,
                    "struct": {"dashboard": [{"element": "value", "format": "raw"}]},
                }
            ],
        },
    ],
}


def create_scene(mod: str, cls: str, title: str, data: list[dict], theme: Themes, rows: int, cols: int):
    """Create a QGraphicsScene with various items."""
    scene = GridGraphicsView(rows=cols, cols=rows, grid_size=CONFIG["grid_size"], theme=theme)
    controller = WidgetGridController(scene)
    # Create a blue rectangle
    args = (title, "/demo", {}, scene, rows, cols, None)
    rect_item: WidgetItem = getattr(importlib.import_module(mod), cls)(*args)
    for item in data:
        rect_item.update_data(item)
    rect_item.update()
    controller.add_to_pos(rect_item, 0, 0)

    return scene, controller, rect_item, args


def capture_scene_to_image(scene: GridGraphicsView, width, height, output_path):
    # Create a QImage with the specified dimensions
    image = QImage(width, height, QImage.Format_ARGB32)
    image.setDotsPerMeterX(int(CONFIG["dpi"] * 39.37))  # Convert DPI to dots per meter
    image.setDotsPerMeterY(int(CONFIG["dpi"] * 39.37))  # Convert DPI to dots per meter
    image.fill(Qt.transparent)

    # Create a painter to draw the scene onto the image
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)

    scene.scene().render(painter)
    painter.end()

    # Save the image to the specified file
    image.save(output_path)
    logger.info(f"Screenshot saved to: {output_path}")


def main():
    """Main function to create and capture a scene."""
    app = QApplication(sys.argv)
    theme = Theme(ThemeStyle.Dark)

    for item in CONFIG["items"]:
        theme.set_style(ThemeStyle.Dark)
        theme.apply(app)
        qtawesome.dark(app)
        scene, controller, witem, args = create_scene(
            item["mod"], item["class"], item["title"], item.get("data", []), Themes.Dark, *item["span"]
        )
        if "wait" in item:
            start = time.time()
            while time.time() - item["wait"] < start:
                app.processEvents()
        if "perdata_wait" in item:
            for data in item["data"]:
                start = time.time()
                while time.time() - start < item["perdata_wait"]:
                    app.processEvents()
                    witem.update_data(data)
                    witem.update()
                    time.sleep(item["perdata_wait"])
        scene.set_theme(Themes.Dark)
        capture_scene_to_image(
            scene,
            width=item["span"][0] * CONFIG["grid_size"],
            height=item["span"][1] * CONFIG["grid_size"],
            output_path=item["out"].format("dark"),
        )
        witem.close()
        scene.deleteLater()
        controller.deleteLater()

        theme.set_style(ThemeStyle.Light)
        theme.apply(app)
        qtawesome.light(app)
        scene, controller, witem, args = create_scene(
            item["mod"], item["class"], item["title"], item.get("data", []), Themes.Light, *item["span"]
        )
        if "wait" in item:
            start = time.time()
            while time.time() - item["wait"] < start:
                app.processEvents()
        if "perdata_wait" in item:
            for data in item["data"]:
                start = time.time()
                while time.time() - start < item["perdata_wait"]:
                    app.processEvents()
                    witem.update_data(data)
                    witem.update()
                    time.sleep(item["perdata_wait"])
        capture_scene_to_image(
            scene,
            width=item["span"][0] * CONFIG["grid_size"],
            height=item["span"][1] * CONFIG["grid_size"],
            output_path=item["out"].format("light"),
        )
        witem.close()
        scene.deleteLater()
        controller.deleteLater()

    # No need to show any GUI or enter the event loop
    # Just exit the application
    sys.exit(0)


if __name__ == "__main__":
    main()
