
import time

from kevinbotlib.joystick import LocalXboxController, XboxControllerButtons

controller = LocalXboxController(0)
controller.start_polling()

try:
    while True:
        if controller.get_button_state(XboxControllerButtons.A):
            print("A button is being held.")
        if controller.get_button_state(XboxControllerButtons.B):
            print("B button is being held.")
        if controller.get_button_state(XboxControllerButtons.X):
            print("X button is being held.")
        if controller.get_button_state(XboxControllerButtons.Y):
            print("Y button is being held.")
        if controller.get_button_state(XboxControllerButtons.LeftBumper):
            print("LB button is being held.")
        if controller.get_button_state(XboxControllerButtons.RightBumper):
            print("RB button is being held.")
        if controller.get_button_state(XboxControllerButtons.LeftStick):
            print("Left stick button is being held.")
        if controller.get_button_state(XboxControllerButtons.RightStick):
            print("Right stick button is being held.")
        if controller.get_button_state(XboxControllerButtons.Back):
            print("Back button is being held.")
        if controller.get_button_state(XboxControllerButtons.Start):
            print("Start button is being held.")
        if controller.get_button_state(XboxControllerButtons.Guide):
            print("Guide button is being held.")
        if controller.get_button_state(XboxControllerButtons.Share):
            print("Share button is being held.")
        time.sleep(.1)
except KeyboardInterrupt:
    controller.stop()
