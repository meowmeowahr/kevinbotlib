import time

from kevinbotlib.joystick import LocalJoystickIdentifiers

while True:
    count = LocalJoystickIdentifiers.get_count()
    names = LocalJoystickIdentifiers.get_names()
    guids = LocalJoystickIdentifiers.get_guids()
    print(f"{count} joysticks present")
    print(f"Joystick Names: {names}")
    print(f"Joystick GUIDs: {guids}")
    time.sleep(1)
