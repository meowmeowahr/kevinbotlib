from kevinbotlib.apps.dashboard.widgets.biglabel import BigLabelWidgetItem
from kevinbotlib.apps.dashboard.widgets.boolean import BooleanWidgetItem
from kevinbotlib.apps.dashboard.widgets.label import LabelWidgetItem
from kevinbotlib.apps.dashboard.widgets.mjpeg import MjpegCameraStreamWidgetItem
from kevinbotlib.apps.dashboard.widgets.textedit import TextEditWidgetItem


def determine_widget_types(did: str):
    match did:
        case "kevinbotlib.dtype.int":
            return {"Basic Text": LabelWidgetItem, "Text Edit": TextEditWidgetItem, "Big Text": BigLabelWidgetItem}
        case "kevinbotlib.dtype.float":
            return {"Basic Text": LabelWidgetItem, "Text Edit": TextEditWidgetItem, "Big Text": BigLabelWidgetItem}
        case "kevinbotlib.dtype.str":
            return {"Basic Text": LabelWidgetItem, "Text Edit": TextEditWidgetItem, "Big Text": BigLabelWidgetItem}
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
