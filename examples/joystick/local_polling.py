import time

from kevinbotlib.joystick import RawLocalJoystickDevice

controller = RawLocalJoystickDevice(0)
controller.start_polling()

try:
    while True:
        print(controller.get_buttons())
        time.sleep(0.1)
except KeyboardInterrupt:
    controller.stop()
