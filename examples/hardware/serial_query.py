from pprint import pprint

from kevinbotlib.hardware.interfaces.serial import SerialIdentification

pprint(SerialIdentification.list_device_info())
