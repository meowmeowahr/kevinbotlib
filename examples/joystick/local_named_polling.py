import time

from kevinbotlib.joystick import LocalNamedController
from kevinbotlib.logger import Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration())

controller = LocalNamedController(0)
controller.start_polling()

try:
    while True:
        print("Held buttons:", [btn.name for btn in controller.get_buttons()])
        print("POV Direction:", controller.get_pov_direction())
        print("Trigger Values:", controller.get_triggers())
        print("Left Stick Values:", controller.get_left_stick())
        print("Right Stick Values:", controller.get_right_stick())
        time.sleep(0.1)
except KeyboardInterrupt:
    controller.stop()
