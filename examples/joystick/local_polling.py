import time

from kevinbotlib.joystick import RawLocalJoystickDevice
from kevinbotlib.logger import Level, Logger, LoggerConfiguration

if __name__ == "__main__":
    logger = Logger()
    logger.configure(LoggerConfiguration(level=Level.TRACE))

    controller = RawLocalJoystickDevice(0)
    controller.start_polling()

    try:
        while True:
            print("Buttons:", controller.get_buttons())
            # print("POV:", controller.get_pov_direction())
            print("Axes:", controller.get_axes())
            time.sleep(0.1)
    except KeyboardInterrupt:
        controller.stop()
