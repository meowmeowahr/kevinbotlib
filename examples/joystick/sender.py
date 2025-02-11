import time

from kevinbotlib.comm import KevinbotCommClient
from kevinbotlib.joystick import JoystickSender, RawLocalJoystickDevice
from kevinbotlib.logger import Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration())

controller = RawLocalJoystickDevice(0)
controller.start_polling()

client = KevinbotCommClient()
client.connect()

sender = JoystickSender(client, controller, "joysticks/0")

while True:
    time.sleep(1)
