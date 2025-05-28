import time

from kevinbotlib.comm import RedisCommClient
from kevinbotlib.joystick import RemoteNamedController
from kevinbotlib.logger import Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration())

client = RedisCommClient()
client.connect()
client.wait_until_connected()

controller = RemoteNamedController(client, "joysticks/0")
controller.start_polling()

try:
    while True:
        print("Buttons:", controller.get_buttons())
        print("POV:", controller.get_pov_direction())
        print("Trigger Values:", controller.get_triggers())
        print("Left Stick Values:", controller.get_left_stick())
        print("Right Stick Values:", controller.get_right_stick())
        print("Connected:", controller.is_connected())
        time.sleep(0.1)
except KeyboardInterrupt:
    controller.stop()
