# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import Kevinbot, Servos

robot = Kevinbot()
robot.connect("/dev/ttyAMA2", 921600, 5, 1)

servos = Servos(robot)

robot.request_enable()  # Ask the core to enable
while not robot.get_state().enabled:  # Wait until the core is enabled
    time.sleep(0.01)

while True:
    inp = input("Servo? ")
    print(f"Bank: {servos[int(inp)].bank}")
    for i in range(181):
        servos[int(inp)].angle = i
        time.sleep(0.02)
        print(i)
    for i in reversed(range(181)):
        servos[int(inp)].angle = i
        time.sleep(0.02)
        print(i)