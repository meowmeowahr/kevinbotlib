import time

from kevinbotlib.joystick import RawLocalJoystickDevice
from kevinbotlib.logger import Logger, LoggerConfiguration

if __name__ == "__main__":
    logger = Logger()
    logger.configure(LoggerConfiguration())

    controller = RawLocalJoystickDevice(0)
    controller.start_polling()

    try:
        while True:
            print("Buttons:", controller.get_buttons())
            print("POV:", controller.get_pov_direction())
            print("Axes:", controller.get_axes())
            time.sleep(0.1)
    except KeyboardInterrupt:
        controller.stop()
