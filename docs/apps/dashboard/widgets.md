# Widgets

## Base Widget

![base-dark.png](../../media/dashboard/base-dark.png#only-dark){width=192px}
![base-light.png](../../media/dashboard/base-light.png#only-light){width=192px}

This widget is used internally within KevinbotLib Dashboard.
It cannot be added from a network sendable. 
It may replace a widget in the case of an error.

## Text Widget

![text-dark.png](../../media/dashboard/text-dark.png#only-dark){width=192px}
![text-light.png](../../media/dashboard/text-light.png#only-light){width=192px}

This is the most basic widget. 
It will display text from a sendable structure. 
Each dashboard structure element will be displayed in a new line.

### Compatible Data Types

* `StringSendable`
* `IntegerSendable`
* `FloatSendable`
* `BooleanSendable`
* `AnyListSendable`
* `DictSendable`
* `BinarySendable`

## Big Text Widget

![bigtext-dark.png](../../media/dashboard/bigtext-dark.png#only-dark){width=192px}
![bigtext-light.png](../../media/dashboard/bigtext-light.png#only-light){width=192px}

This widget functions the same as the [Text Widget](#text-widget), but with larger text. 
The text size will automatically adjust to its content and grid span.

### Compatible Data Types

* `StringSendable`
* `IntegerSendable`
* `FloatSendable`
* `BooleanSendable`
* `AnyListSendable`
* `DictSendable`

## Editable Text Widget

![textedit-dark.png](../../media/dashboard/textedit-dark.png#only-dark){width=192px}
![textedit-light.png](../../media/dashboard/textedit-light.png#only-light){width=192px}

This widget allows for the editing of text, integers, and floating-point values. 

Editing the text line will cause the widget to enter "edit mode," indicated by a red cross by the text line. 
While in edit mode, new data received will not be displayed.

Pressing the "Submit" button will repackage the last sendable received with the updated text, and send it back to the robot.
This will also exit "edit mode."

Pressing the "Cancel" button will exit "edit mode," and cause the data to reset.

### Compatible Data Types

* `StringSendable`
* `IntegerSendable`
* `FloatSendable`

## Boolean Widget

![boolean-off-dark.png](../../media/dashboard/boolean-off-dark.png#only-dark){width=192px}
![boolean-off-light.png](../../media/dashboard/boolean-off-light.png#only-light){width=192px}
![boolean-on-dark.png](../../media/dashboard/boolean-on-dark.png#only-dark){width=192px}
![boolean-on-light.png](../../media/dashboard/boolean-on-light.png#only-light){width=192px}

### Compatible Data Types

* `BooleanSendable`

## Color Widget

![color-dark.png](../../media/dashboard/color-dark.png#only-dark){width=192px}
![color-light.png](../../media/dashboard/color-light.png#only-light){width=192px}

### Compatible Data Types

* `StringSendable`

## MJPEG Streamer Widget

![mjpeg-dark.png](../../media/dashboard/mjpeg-dark.png#only-dark){width=576px}
![mjpeg-light.png](../../media/dashboard/mjpeg-light.png#only-light){width=576px}

### Compatible Data Types

* `kevinbotlib.vision.MjpegStreamSendable`

## Battery Widget

![battery-dark.png](../../media/dashboard/battery-dark.png#only-dark){width=192px}
![battery-light.png](../../media/dashboard/battery-light.png#only-light){width=192px}

### Compatible Data Types

* `FloatSendable`

## Speedometer Widget

![speedometer-dark.png](../../media/dashboard/speedometer-dark.png#only-dark){width=384px}
![speedometer-light.png](../../media/dashboard/speedometer-light.png#only-light){width=384px}

### Compatible Data Types

* `IntegerSendable`
* `FloatSendable`
