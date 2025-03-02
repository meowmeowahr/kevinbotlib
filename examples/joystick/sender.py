import time

from kevinbotlib.comm import KevinbotCommClient
from kevinbotlib.joystick import JoystickSender, LocalXboxController
from kevinbotlib.logger import Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration())

controller = LocalXboxController(0)
controller.start_polling()

client = KevinbotCommClient()
client.connect()
client.wait_until_connected()

sender = JoystickSender(client, controller, "joysticks/0")
sender.start()

while True:
    time.sleep(1)
