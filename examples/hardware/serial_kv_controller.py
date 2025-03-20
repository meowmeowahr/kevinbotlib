import time

from kevinbotlib.hardware.controllers.keyvalue import RawKeyValueSerialController
from kevinbotlib.hardware.interfaces.serial import RawSerialInterface

# ! remember to change these settings for your testing environment
interface = RawSerialInterface(
    "/dev/ttyUSB0", 9600, timeout=1
)  # a timeout is useful to not stall at `controller.read_next()`

controller = RawKeyValueSerialController(interface, b"=", b"\n")

while True:
    print("Sending data")
    controller.write(b"test", b"1")

    pair = controller.read()
    if pair:
        print("Got data:", pair)
    else:
        print("Serial interface timeout")

    time.sleep(1)
