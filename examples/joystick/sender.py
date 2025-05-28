import time

from kevinbotlib.comm import RedisCommClient
from kevinbotlib.joystick import JoystickSender, LocalNamedController
from kevinbotlib.logger import Logger, LoggerConfiguration

logger = Logger()
logger.configure(LoggerConfiguration())

controller = LocalNamedController(
    0
)  # it doesn't matter what type of controller is being sent - all values will be converted to raw anyway
controller.start_polling()

client = RedisCommClient()
client.connect()
client.wait_until_connected()

sender = JoystickSender(client, controller, "joysticks/0")
sender.start()

while True:
    time.sleep(1)
