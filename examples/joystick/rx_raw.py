import time

from kevinbotlib.comm import RedisCommClient
from kevinbotlib.joystick import RemoteRawJoystickDevice
from kevinbotlib.logger import Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration())

client = RedisCommClient()
client.connect()
client.wait_until_connected()

controller = RemoteRawJoystickDevice(client, "joysticks/0")
controller.start_polling()

try:
    while True:
        print("Buttons:", controller.get_buttons())
        print("POV:", controller.get_pov_direction())
        print("Axes:", controller.get_axes())
        print("Connected:", controller.is_connected())
        time.sleep(0.1)
except KeyboardInterrupt:
    controller.stop()
