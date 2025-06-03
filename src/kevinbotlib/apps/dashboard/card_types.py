from kevinbotlib.apps.dashboard.widgets.base import WidgetItem
from kevinbotlib.apps.dashboard.widgets.battery import BatteryWidgetItem
from kevinbotlib.apps.dashboard.widgets.biglabel import BigLabelWidgetItem
from kevinbotlib.apps.dashboard.widgets.boolean import BooleanWidgetItem
from kevinbotlib.apps.dashboard.widgets.color import ColorWidgetItem
from kevinbotlib.apps.dashboard.widgets.graph import GraphWidgetItem
from kevinbotlib.apps.dashboard.widgets.label import LabelWidgetItem
from kevinbotlib.apps.dashboard.widgets.mjpeg import MjpegCameraStreamWidgetItem
from kevinbotlib.apps.dashboard.widgets.speedometer import SpeedometerWidgetItem
from kevinbotlib.apps.dashboard.widgets.textedit import TextEditWidgetItem


def determine_widget_types(did: str):
    match did:
        case "kevinbotlib.dtype.int":
            return {
                "Basic Text": LabelWidgetItem,
                "Text Edit": TextEditWidgetItem,
                "Big Text": BigLabelWidgetItem,
                "Speedometer": SpeedometerWidgetItem,
                "Graph": GraphWidgetItem,
            }
        case "kevinbotlib.dtype.float":
            return {
                "Basic Text": LabelWidgetItem,
                "Text Edit": TextEditWidgetItem,
                "Big Text": BigLabelWidgetItem,
                "Speedometer": SpeedometerWidgetItem,
                "Battery": BatteryWidgetItem,
                "Graph": GraphWidgetItem,
            }
        case "kevinbotlib.dtype.str":
            return {
                "Basic Text": LabelWidgetItem,
                "Text Edit": TextEditWidgetItem,
                "Big Text": BigLabelWidgetItem,
                "Color": ColorWidgetItem,
            }
        case "kevinbotlib.dtype.bool":
            return {"Basic Text": LabelWidgetItem, "Big Text": BigLabelWidgetItem, "Boolean": BooleanWidgetItem}
        case "kevinbotlib.dtype.list.any":
            return {"Basic Text": LabelWidgetItem, "Big Text": BigLabelWidgetItem}
        case "kevinbotlib.dtype.dict":
            return {"Basic Text": LabelWidgetItem, "Big Text": BigLabelWidgetItem}
        case "kevinbotlib.dtype.bin":
            return {"Basic Text": LabelWidgetItem}
        case "kevinbotlib.vision.dtype.mjpeg":
            return {"MJPEG Stream": MjpegCameraStreamWidgetItem}
    return {}


def item_loader(self, item: dict) -> WidgetItem:
    kind = item["kind"]
    title = item["title"]
    options = item["options"] if "options" in item else {}
    span_x = item["span_x"]
    span_y = item["span_y"]
    key = item["key"] if "key" in item else item["title"]
    match kind:
        case "base":
            return WidgetItem(title, key, options, self.graphics_view, span_x, span_y, self.client)
        case "text":
            return LabelWidgetItem(title, key, options, self.graphics_view, span_x, span_y, self.client)
        case "bigtext":
            return BigLabelWidgetItem(title, key, options, self.graphics_view, span_x, span_y, self.client)
        case "textedit":
            return TextEditWidgetItem(title, key, options, self.graphics_view, span_x, span_y, self.client)
        case "boolean":
            return BooleanWidgetItem(title, key, options, self.graphics_view, span_x, span_y, self.client)
        case "cameramjpeg":
            return MjpegCameraStreamWidgetItem(title, key, options, self.graphics_view, span_x, span_y, self.client)
        case "color":
            return ColorWidgetItem(title, key, options, self.graphics_view, span_x, span_y, self.client)
        case "speedometer":
            return SpeedometerWidgetItem(title, key, options, self.graphics_view, span_x, span_y, self.client)
        case "graph":
            return GraphWidgetItem(title, key, options, self.graphics_view, span_x, span_y, self.client)
        case "battery":
            return BatteryWidgetItem(title, key, options, self.graphics_view, span_x, span_y, self.client)

    return WidgetItem(title, key, options, self.graphics_view, span_x, span_y)
